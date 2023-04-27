import threading, grpc, exchange_pb2_grpc, exchange_pb2, random, time
from concurrent import futures

class nFaultStub:
    def __init__(self):
        self.stub_dict = {
            "stub": None,
            "port": None
        }
        self.backup_stub_dict = {
            "stub": None,
            "port": None
        }
        self.SERVERS = Constants.SERVER_IPS.copy()

        self.backup_stub_connect_thread = threading.Thread(target = self.background_connect, daemon=True)
        self.backup_stub_connect_thread.start()

    
    def background_connect(self):
        while True:

            time.sleep(Constants.BACKGROUND_STUB_REFRESH_RATE)

            try:
                self.backup_stub_dict["stub"].Ping(exchange_pb2.Empty())
            except:
                shuffle_servers = [(port, host) for port, host in self.SERVERS.items() if port != self.stub_dict["port"]]
                random.shuffle(shuffle_servers)

                for port, host in shuffle_servers:
                    try:
                        channel = grpc.insecure_channel(host + ':' + str(port)) 
                        self.backup_stub_dict["stub"] = exchange_pb2_grpc.ExchangeServiceStub(channel)
                        self.backup_stub_dict["stub"].Ping(exchange_pb2.Empty())
                        self.backup_stub_dict["port"] = port
                        break
                    except:
                        print(f"Backup could not connect to {host}:{port}")
            

    def connect(self) -> bool:
        shuffle_servers = list(self.SERVERS.items())
        random.shuffle(shuffle_servers)

        for port, host in shuffle_servers:
            try:
                channel = grpc.insecure_channel(host + ':' + str(port)) 
                self.stub_dict["stub"] = exchange_pb2_grpc.ExchangeServiceStub(channel)
                self.stub_dict["stub"].Ping(exchange_pb2.Empty())
                self.stub_dict["port"] = port

                print(f"Client connected to server w/ port {port}")

                self.backup_stub_connect_thread.start()
                return True
            except:
                print(f"Could not connect to {host}:{port}")
        
        return False
    
    def __getattr__(self, name):
        def wrapper(*args, **kwargs):
            for _ in range(len(self.SERVERS)):
                try:
                    func = getattr(self.stub_dict["stub"], name)
                    response = func(*args, **kwargs)
                    return response
                except grpc.RpcError as e:
                    print(f"An error occurred while calling {name}: {e}")
                    self.stub_dict, self.backup_stub_dict = self.backup_stub_dict, self.stub_dict
                    print(f"Client connected to server w/ port {self.stub_dict['port']}")
                    
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