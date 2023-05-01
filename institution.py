import socket, threading, time, grpc, os
import exchange_pb2
from exchange_pb2_grpc import BrokerServiceServicer, BrokerServiceStub, add_BrokerServiceServicer_to_server
import constants as c
from helpers import TwoFaultStub
from typing import Dict, List, Tuple
from concurrent import futures

FEE = 1

class Institution():
    def __init__(self) -> None:
        self.balance = 10000        
        self.held_stocks = []
        self.stub = TwoFaultStub()
        self.stub.connect()
    
    def receive_pings(self):
        while True:
            self.stub.Ping(exchange_pb2.Empty())
            time.sleep(3)
    
if __name__ == "__main__":
    institution = Institution()
    threading.Thread(target=institution.receive_pings).start()

