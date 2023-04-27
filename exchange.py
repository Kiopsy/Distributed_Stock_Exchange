import socket, threading, time, grpc, pickle, os
import exchange_pb2
from exchange_pb2_grpc import ExchangeServiceServicer, ExchangeServiceStub, add_ExchangeServiceServicer_to_server
from helpers import ThreadSafeSet
import constants as c
from concurrent import futures
from limit_order_book import LimitOrderBook, User
from database import Database
from collections import defaultdict, deque

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
        self.PEER_PORTS : dict[int, str] = c.SERVER_IPS.copy()
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
        if not os.path.exists(c.LOG_DIR):
            os.makedirs(c.LOG_DIR)
        self.LOG_FILE_NAME = f"./{c.LOG_DIR}/server{self.ID}.log"
        self.log_file = open(self.LOG_FILE_NAME , "w")

        # init pkl file
        if not os.path.exists(c.PKL_DIR):
            os.makedirs(c.PKL_DIR)
        self.PKL_FILE_NAME = f"./{c.PKL_DIR}/server{self.ID}.pkl"
        
        # TREAT LIKE A DICTIONARY; load the database (create if it does not exist)
        self.db = Database(filename=self.PKL_FILE_NAME)
    
        # thread safe set that tracks if a ballot id has been seen
        self.seen_ballots = ThreadSafeSet()

        # keep track of filled orders. user -> a queue of their filled orders
        self.order_fills = defaultdict(deque)

    # func "sprint": prints within a server
    def sprint(self, *args, **kwargs) -> None:
        if not self.SILENT:
            print(f"Server {self.ID}:", *args, **kwargs)

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
                    revive_info: exchange_pb2.ReviveInfo = self.peer_stubs[port].Alive(exchange_pb2.Empty())

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
    
    # func "revive": incorporate the receieved revive info
    def revive(self, revive_info: exchange_pb2.ReviveInfo) -> None:
        self.primary_port = revive_info.primary_port

        self.sprint("Received primary: ", self.primary_port)

        try:
            # clear log file and rewrite with revive_info file !!
            self.log_file.truncate(0)
            self.log_file.write(revive_info.commit_log)
            self.log_file.flush()

            # update db to be like the log file OR use binary sent data to be the new db
            # TODO: probably should not cheese it like this ("this" being passing in bytes)
            self.db.turn_bytes_into_db(revive_info.db_bytes)

        except:
            self.sprint("Some log/db updating conflict")
    
    # rpc func "Alive": takes in Empty and returns updates
    def Alive(self, request, context):
        # only the primary can send over revive info (aka commit log)
        if self.primary_port == self.PORT:
            try:
                with open(self.LOG_FILE_NAME, 'r') as file:
                    text_data = file.read()
                with open(self.PKL_FILE_NAME, 'rb') as dbfile:
                    db_bytes = pickle.dumps(pickle.load(dbfile))
            except:
                text_data = ""
                db_bytes = bytes()
            return exchange_pb2.ReviveInfo(
                primary_port = self.primary_port, 
                commit_log = text_data,
                db_bytes = db_bytes, 
                updates = True)
        else:
            return exchange_pb2.ReviveInfo(updates = False)

    # HEARTBEAT SECTION

    # func "leader_election": uses the bully algorithm to elect the machine with the lowest port as the leader
    def leader_election(self) -> int:
        alive_ports = (port for port, alive in [*self.peer_alive.items(), (self.PORT, True)] if alive)
        self.primary_port = min(alive_ports)
        self.sprint(f"New primary: {self.primary_port}")
        return self.primary_port
    
    # func "receive_heartbeat": ask all other machines if they are alive by asking of
    def receive_heartbeat(self) -> None:

        def individual_heartbeat(port: int) -> None:
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
    def revive(self, revive_info):
        pass

    # CONSENSUS VOTING SECTION

    # func "send_commit_proposal" : proposes a commit, if all peers agree on it: it is commited; else: it is rejected
    def send_commit_proposal(self, commit) -> bool:

        # sets the ballot id to the largest unseen ballot
        ballot_id = self.seen_ballots.max() + 1
        self.seen_ballots.add(ballot_id)
        
        approved = True
        living_stubs = lambda: [(self.peer_stubs[port], port) for port in self.peer_alive if self.peer_alive[port]]

        # sends the commit request to all living peers and tallies their responses
        for stub, port in living_stubs():
            req = exchange_pb2.CommitRequest(commit = commit, ballot_id = ballot_id)
            try:
                response : exchange_pb2.CommitVote = stub.ProposeCommit(req)
                approved &= response.approve
            except:
                self.sprint(port, "died when voting; vote rejected")
                approved = False
                self.peer_alive[port] = False

        # sends the result of the vote to all living peers
        for stub, port in living_stubs():

            vote = exchange_pb2.CommitVote(commit = commit, approve = approved, ballot_id = ballot_id)
            try:
                stub.SendVoteResult(vote)
            except:
                self.sprint(port, "died when confirming vote")
                self.peer_alive[port] = False

        # commits changes if vote was approved
        if approved:
            # add commit
            self.write_to_log(commit, ballot_id)
        else:
            self.sprint("*Rejected commit")

        return approved

    # func "write_to_log": writes a commit to the log file
    def write_to_log(self, commit, ballot_id):
        # TODO: if not connected, wait until connected to add these commits
        self.sprint(f"Added commit {commit} w/ ballot_id {ballot_id}")
        self.log_file.write(f"{ballot_id}# {commit}\n")
        self.log_file.flush()

    # rpc func "ProposeCommit": takes a CommitRequest/Proposal as input, returns an approving vote iff the ballot id is unseen
    def ProposeCommit(self, request, context):
        approved = request.ballot_id not in self.seen_ballots
        self.seen_ballots.add(request.ballot_id)
        return exchange_pb2.CommitVote(approve = approved)
    
    # rpc func "SendVoteResult": takes a CommitVote/Final verdict as input, adds commit if approved, returns Empty
    def SendVoteResult(self, request, context):
        if request.approve:
            # add commit
            commit, ballot_id = request.commit, request.ballot_id
            self.write_to_log(commit, ballot_id)
            # TODO: update db
            # Prolly use state machine mumbo jumbo
            #
            # Old code using exec cheese:
            commands = commit.split(c.DIVIDER)
            for cmd in commands:
                exec(cmd)
            self.db.store_data()
        else:
            self.sprint("Rejected commit")

        return exchange_pb2.Empty()
    
    def vote_on_client_request(self, commit_state: str) -> bool:
        success = False
        for _ in range(c.MAX_VOTE_ATTEMPTS):
            if self.send_commit_proposal(commit_state):
                success = True
                break
        return success

    # CLIENT FUNCTIONS SECTION

    # decorator that only allows clients to connect if the current machine is connected to the peers
    def connection_required(func):
        def wrapper(self, request, context):

            if not self.connected:
                context.set_details("Server currently disconnected.")
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                return grpc.RpcMethodHandler()
            
            return func(self, request, context)
        
        return wrapper

    # WIP
    # rpc func "SendOrder": push an order to the orderbooks, make matches if possible
    @connection_required
    def SendOrder(self, request, context):
        # retreive the order
        ticker = request.ticker
        quantity = request.quantity
        price = request.price
        uid = request.uid
        side = "bid" if request.type == exchange_pb2.OrderType.BID else "ask"

        # retreive orderbook associated with the stock's ticker
        book = self.db.get_db()["orderbooks"][ticker]
        
        res = book.add_order(side, price, quantity, uid) # after matches are made 

        self.db.get_db()["orderbooks"][ticker] = book

    # WIP
    # rpc func "CancelOrder": 
    @connection_required
    def CancelOrder(self, request, context) -> exchange_pb2.Result:
        # request = exchange_pb2.OrderId
        pass
    
    # WIP
    # rpc func "GetOrderList": 
    @connection_required
    def GetOrderList(self, request, context) -> exchange_pb2.OrderInfo:
        # request = exchange_pb2.Empty
        pass

    # WIP
    # rpc func "DepositCash": 
    @connection_required
    def DepositCash(self, request, context) -> exchange_pb2.Result:
        res = False
        if request.uid in self.db.get_db()["client_balance"]:
            state_str = f"self.db.get_db()['client_balance'][{request.uid}] += {request.amount}"
            success = self.vote_on_client_request(state_str)
            if success:
                self.db.get_db()["client_balance"][request.uid] += request.amount
                self.db.store_data()
                res = True  
                
        return exchange_pb2.Result(result = res)

    # WIP
    # rpc func "OrderFill":
    @connection_required
    def OrderFill(self, request, context) -> exchange_pb2.FillInfo:
        pass
        # request = exchange_pb2.UserInfo

    # WIP
    # rpc func "Ping": 
    @connection_required
    def Ping(self, request, context):
        return exchange_pb2.Empty()