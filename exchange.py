import socket, threading, time, grpc, pickle, os
import exchange_pb2 as exchange_pb2
from exchange_pb2_grpc import ExchangeServiceServicer, ExchangeServiceStub, add_ExchangeServiceServicer_to_server
from helpers import Constants as c
from concurrent import futures
from collections import defaultdict
from limit_order_book import LimitOrderBook, User

# func "serve": starts an exchange server
def serve(id: int) -> None:
    exchange = ExchangeServer(id)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_ExchangeServiceServicer_to_server(exchange, server)
    server.add_insecure_port(exchange.HOST + ':' + str(exchange.PORT))
    server.start()
    exchange.sprint(f"Server initialized at {exchange.HOST} on port {exchange.PORT}")
    time.sleep(c.CONNECTION_WAIT_TIME)
    exchange.connect()
    exchange.heartbeat_thread.start()
    server.wait_for_termination()
        
# class that defines an exchange and its server
class ExchangeServer(ExchangeServiceServicer):
    def __init__(self, id: int, silent=False) -> None:
        self.ID = id
        self.SILENT = silent

        # initialize channel constants
        self.HOST = socket.gethostbyname(socket.gethostname())
        self.PORT = 50050 + self.ID

        # dict of the other servers' ports -> their host/ips
        self.PEER_PORTS : dict[int, str] = c.SERVER_IPS.copy() # change "HOST" when we want to use other devices
        del self.PEER_PORTS[self.PORT]

        # dict of the other servers' ports -> bool determining if they are alive
        self.peer_alive = {port: False for port in self.PEER_PORTS}
        self.peer_stubs : dict[int, ExchangeServiceStub] = {}

        # identifies the leading server's port number
        self.primary_port = -1 
        
        # bool dictating if the current server is connected to the other (living) ones
        self.connected = False
        
        # thread to look for heartbeats from the other servers
        self.heartbeat_thread = threading.Thread(target = self.receive_heartbeat, daemon=True)
        self.stop_event = threading.Event()

        # init commit log file
        if not os.path.exists(c.LOGS_DIR):
            os.makedirs(c.LOGS_DIR)
        self.LOG_FILE_NAME = f"./{c.LOGS_DIR}/server{self.ID}.log"
        self.log_file = open(self.LOG_FILE_NAME , "w")

        # init pkl file
        if not os.path.exists(c.PKL_DIR):
            os.makedirs(c.PKL_DIR)
        self.PKL_FILE_NAME = f"./{c.PKL_DIR}/server{self.ID}.pkl"
        
        # load the database (create if it does not exist)
        try:
            with open(self.PKL_FILE_NAME, 'rb')  as dbfile:
                self.db = pickle.load(dbfile)
        except:
            self.db = {
                "orderbooks" : defaultdict(lambda: LimitOrderBook()),
                "client_balance": defaultdict(int)
            }
    
        # thread safe set that tracks if a ballot id has been seen
        self.seen_ballots = set() # ThreadSafeSet()

    # func "sprint": prints within a server
    def sprint(self, *args, **kwargs) -> None:
        if not self.SILENT:
            print("Server {self.ID}", args, kwargs)

    # func "connect": connect current server to peers servers
    def connect(self) -> bool:
        if not self.connected:
            # Form a connection (stub) between all other peers (if they are alive)
            for port, host in self.PEER_PORTS.items():
                try:
                    # form connection (stub)
                    channel = grpc.insecure_channel(host + ':' + str(port)) 
                    self.peer_stubs[port] = ExchangeServiceStub(channel)
                    #  check if the peer is alive
                    revive_info = self.peer_stubs[port].Alive(exchange_pb2.Empty())

                    # if the primary peer has updates to share, update the current server
                    if revive_info.updates:
                        self.revive(revive_info)

                    self.peer_alive[port] = True
                except Exception as e:
                    self.sprint("Received Error in Connect:", e)
                    self.peer_alive[port] = False

        if self.primary_port == -1:
            self.leader_election()

        self.connected = True
        self.sprint("Connected", self.peer_alive)
        return self.connected
    
    # rpc func "Alive": takes in Empty and returns updates
    def Alive(self, request, context):
        # only the primary can send over revive info (aka commit log)
        if self.primary_port == self.PORT:
            try:
                with open(self.LOG_FILE_NAME, 'r') as file:
                    text_data = file.read()
            except:
                text_data = ""
            return exchange_pb2.ReviveInfo(
                primary_port = self.primary_port, 
                commit_log = text_data, 
                updates = True)
        else:
            return exchange_pb2.ReviveInfo(updates = False)
    
    # func "receive_heartbeat": ask all other machines if they are alive by asking of
    def receive_heartbeat(self) -> None:

        def individual_heartbeat(port):
            # every HEARTRATE seconds, ask given port for heartbeats
            stub = self.peer_stubs[port]
            while not self.stop_event.is_set():
                time.sleep(c.HEARTRATE)
                try:
                    response : exchange_pb2.HeartbeatResponse = stub.RequestHeartbeat(exchange_pb2.Empty())
                    if self.peer_alive[response.port] == False:
                        self.sprint(f"{response.port} is back online")
                    self.peer_alive[response.port] = True
                except:
                    # if cannot connect to a peer, mark it as dead
                    if self.peer_alive[port]:
                        self.sprint(f"Heartbeat not received from port {port}")
                    self.peer_alive[port] = False
                    if self.primary_port == port: # run an election if the primary has died 
                        self.leader_election()

        for port in self.peer_stubs:
            threading.Thread(target = individual_heartbeat, args=(port, ), daemon=True).start()

    # func "stop_machine": stop the machine's heartbeat by setting stop_event
    def stop_machine(self):
        self.stop_event.set() 
        self.heartbeat_thread.join()

    # rpc func "RequestHeartbeat": takes Empty as input and retuns its port
    def RequestHeartbeat(self, request, context):
        return exchange_pb2.HeartbeatResponse(port=self.PORT)
    
    # func "revive": revive's a server based on the primary's commit log
    def revive(self, revive_info: ):
        pass

    # func "leader_election": uses the bully algorithm to elect the machine with the lowest port as the leader
    def leader_election(self) -> int:
        alive_ports = (port for port, alive in [*self.peer_alive.items(), (self.PORT, True)] if alive)
        self.primary_port = min(alive_ports)
        self.sprint(f"New primary: {self.primary_port}")
        return self.primary_port
    
    # rpc func "SendOrder": 
    def SendOrder(self, request, context):
        return super().SendOrder(request, context)

    def Ping(self, request, context):
        return exchange_pb2.Empty()
    
    """
    1.  Copy/paste paxos algo and make it work with our current DB (not 
        sure if it needs to change)
    2.  Start thinking about the state machine and how we read each line from
        the commit file
    3.  Write the revive function that takes the commit log from the primary
        and compares with its own log and revives itself using state machine.

        Do not worry about where exactly paxos will be run. I will implement this
        when working with Gianni on the receive end of the broker's RPC calls 
    """