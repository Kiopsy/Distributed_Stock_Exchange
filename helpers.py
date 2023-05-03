import threading, grpc, exchange_pb2_grpc, exchange_pb2, random, time, multiprocessing, sys
from concurrent import futures
import constants as c

class nFaultStub:
    def __init__(self):
        # Each stub dict holds the stub itself and its associated port
        self.stub_dict = {
            "stub": None,
            "port": None
        }
        self.backup_stub_dict = {
            "stub": None,
            "port": None
        }

        # A dict that has the port and host name of all possible servers to connect to
        self.SERVERS = c.SERVER_IPS.copy()

        # A thread that constanlty makes sure the backup thread is connected to anotehr available server
        self.backup_stub_connect_thread: threading.Thread = threading.Thread(target = self.background_connect, daemon=True)

    def background_connect(self):
        # Every BACKGROUND_STUB_REFRESH_RATE seconds, check if the bg_stub is alive by pinging
        while True:

            time.sleep(c.BACKGROUND_STUB_REFRESH_RATE)

            try:
                self.backup_stub_dict["stub"].Ping(exchange_pb2.Empty())
            except:
                # try to connect to a random server that the main server is not connected to 
                shuffle_servers = [(port, host) for port, host in self.SERVERS.items() if port != self.stub_dict["port"]]
                random.shuffle(shuffle_servers)

                for port, host in shuffle_servers:
                    try:
                        channel = grpc.insecure_channel(host + ':' + str(port)) 
                        self.backup_stub_dict["stub"] = exchange_pb2_grpc.ExchangeServiceStub(channel)
                        self.backup_stub_dict["stub"].Ping(exchange_pb2.Empty())
                        self.backup_stub_dict["port"] = port
                        print(f"Backup connected to port {port}")
                        break
                    except:
                        print(f"Backup could not connect to {host}:{port}")

    def connect(self) -> bool:

        # Shuffle the servers so we don't start predicitbaly with the lowest one
        shuffle_servers = list(self.SERVERS.items())
        random.shuffle(shuffle_servers)

        for port, host in shuffle_servers:
            try:
                channel = grpc.insecure_channel(host + ':' + str(port)) 

                # Try connecting the stub first, and then the backup stub
                if self.stub_dict["port"] == None:
                    self.stub_dict["stub"] = exchange_pb2_grpc.ExchangeServiceStub(channel)
                    self.stub_dict["stub"].Ping(exchange_pb2.Empty())
                    self.stub_dict["port"] = port
                    print(f"Main stub connected to server w/ port {port}")
                else:
                    self.backup_stub_dict["stub"] = exchange_pb2_grpc.ExchangeServiceStub(channel)
                    self.backup_stub_dict["stub"].Ping(exchange_pb2.Empty())
                    self.backup_stub_dict["port"] = port
                    print(f"Backup stub connected to server w/ port {port}")
                
                # If both are connected return true
                if self.stub_dict["port"] and self.backup_stub_dict["port"]:
                    return True
            except:
                print(f"Could not connect to {host}:{port}")
        
        # Return true if the main stub was able to connect
        return self.stub_dict["port"] != None
    
    def __getattr__(self, name):
        def wrapper(*args, **kwargs):
            # for each possible server
            for i in range(len(self.SERVERS)):
                
                try: # try calling the function on the stub
                    func = getattr(self.stub_dict["stub"], name)
                    response = func(*args, **kwargs)
                    return response
                except Exception as e: # On any failure, switch stub and backup stub
                    print(f"An error occurred while calling {name}: {e}")
                    self.stub_dict, self.backup_stub_dict = self.backup_stub_dict, self.stub_dict
                    if i != len(self.SERVERS) - 1:
                        print(f"Switching to backup connected to port {self.stub_dict['port']}")
                    else:
                        print("No servers online")

        return wrapper

class ThreadSafeSet:
    def __init__(self):
        self._set = set()
        self._lock = threading.Lock()
        self._max = 0
    
    def max(self):
        with self._lock:
            return self._max

    def add(self, item):
        with self._lock:
            self._set.add(item)
            self._max = max(self._max, item)

    def remove(self, item):
        with self._lock:
            self._set.remove(item)

    def __contains__(self, item):
        with self._lock:
            return item in self._set

    def __len__(self):
        with self._lock:
            return len(self._set)
        
    def __iter__(self):
        with self._lock:
            return iter(self._set)


# clean control c exiting
def sigint_handler(signum, frame):
    # terminate all child processes
    for process in multiprocessing.active_children():
        process.terminate()
    # exit the main process without raising SystemExit
    try:
        sys.exit(0)
    except SystemExit:
        pass