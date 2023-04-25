import socket, threading, time, grpc
import exchange_pb2 as exchange_pb2
from exchange_pb2_grpc import ExchangeServiceServicer, ExchangeServiceStub, add_ChatServiceServicer_to_server
from constants import Constants as c
from concurrent import futures

# func "serve": starts an exchange server
def serve(id):
    exchange = ExchangeServer(id)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_ChatServiceServicer_to_server(exchange, server)
    server.add_insecure_port(exchange.HOST + ':' + str(exchange.PORT))
    server.start()
    exchange.sprint(f"Server initialized at {exchange.HOST} on port {exchange.PORT}")
    time.sleep(3)
    exchange.connect()
    exchange.heartbeat_thread.start()
    server.wait_for_termination()
        
# class that defines an exchange and its server
class ExchangeServer(ExchangeServiceServicer):
    def __init__(self, id, silent=False) -> None:
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

        # initialization of the commit log file
        # if not os.path.exists(LOGS_DIR):
        #     os.makedirs(LOGS_DIR)
        # self.LOG_FILE_NAME = f"./{LOGS_DIR}/machine{self.MACHINE_ID}.log"
        # self.log_file = open(self.LOG_FILE_NAME , "w")
        
        # thread safe set that tracks if a ballot id has been seen
        self.seen_ballots = set() # ThreadSafeSet()

    # func "sprint": prints within a server
    def sprint(self, *args, end = "\n") -> None:
        if not self.SILENT:
            print(f"Server {self.ID}: {' '.join(str(x) for x in args)}", end = end)

    def SendVoteResult(self, request, context):
        return super().SendVoteResult(request, context)
