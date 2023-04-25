import socket, threading, futures, time, grpc
import exchange_pb2 as exchange_pb2
from exchange_pb2_grpc import BrokerServiceServicer, BrokerServiceStub, add_BrokerServiceServicer_to_server
from constants import Constants as c

class Broker(BrokerServiceServicer):
    def __init__(self, id, silent=False) -> None:
        pass

