import threading, grpc, exchange_pb2_grpc, exchange_pb2
from concurrent import futures
import random
import threading

class Constants:
    SERVER_IPS = {50050: "10.252.70.134", 50051: "10.252.70.134", 50052: "10.252.70.134"}
    # 10.252.80.70
    HEARTRATE = 3

    NUM_SERVERS = 3

    CONNECTION_WAIT_TIME = 3

    EXCHANGE_FEE = 1

    LOG_DIR = "logs"

    PKL_DIR = "pickles"

    TICKERS = ["GOOGL", "AAPL", "MSFT"]

class TwoFaultStub:
    def __init__(self):
        self.stub: list[exchange_pb2_grpc.ExchangeServiceStub, int] = [None, None]
        self.backup_stub: list[exchange_pb2_grpc.ExchangeServiceStub, int] = [None, None]
        self.SERVERS = Constants.SERVER_IPS
    
    def connect_stub(self):
        shuffle_servers = list(self.SERVERS.items())
        random.shuffle(shuffle_servers)

        

        for port, host in shuffle_servers:
            try:
                channel = grpc.insecure_channel(host + ':' + str(port)) 
                self.stub = exchange_pb2_grpc.ExchangeServiceStub(channel)
                self.stub.Ping(exchange_pb2.Empty())

                print(f"Client connected to server w/ port {port}")
                return True
            except:
                print(f"Could not connect to {host}:{port}")



    def connect(self) -> bool:
        shuffle_servers = list(self.SERVERS.items())
        random.shuffle(shuffle_servers)

        for port, host in shuffle_servers:
            try:
                channel = grpc.insecure_channel(host + ':' + str(port)) 
                self.stub = exchange_pb2_grpc.ExchangeServiceStub(channel)
                self.stub.Ping(exchange_pb2.Empty())

                print(f"Client connected to server w/ port {port}")
                return True
            except:
                print(f"Could not connect to {host}:{port}")
        
        return False
    
    
    def __getattr__(self, name):
        def wrapper(*args, **kwargs):
            for _ in range(3):
                try:
                    func = getattr(self.stub, name)
                    response = func(*args, **kwargs)
                    return response
                except grpc.RpcError as e:
                    print(f"An error occurred while calling {name}: {e}")
                    self.connect()
                    
            print("No servers online")
        return wrapper