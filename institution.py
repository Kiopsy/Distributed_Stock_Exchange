import socket, threading, time, grpc, os
import exchange_pb2
from exchange_pb2_grpc import BrokerServiceServicer, BrokerServiceStub, add_BrokerServiceServicer_to_server
import constants as c
from helpers import nFaultStub 
from typing import Dict, List, Tuple
from concurrent import futures

class InstitutionClient():
    def __init__(self, uid) -> None:
        self.stub = nFaultStub()
        self.stub.connect()
        self.uid = uid

    def SendOrder(self, order_type, ticker: str, quantity: int, price: int, uid) -> Tuple[str, bool]:
        try:
            oid =self.stub.SendOrder(exchange_pb2.OrderInfo(ticker=ticker,
                                                            quantity=quantity,
                                                            price=price,
                                                            uid=uid,
                                                            type=order_type))
            return ("Order sent", not oid.oid == -1)
        except Exception as e:
            return (f"Error: {str(e)}", not oid.oid == -1)
        
    def DepositCash(self, uid: int, amount: int) -> None:
        self.stub.DepositCash(exchange_pb2.Deposit(uid=uid, amount=amount))
    
    def CancelOrder(self, oid: int) -> None:
        try:
            self.stub.CancelOrder(exchange_pb2.CancelRequest(uid=self.uid, 
                                                             oid=oid))
        except Exception as e:
            print(f"Error: {e}")
    
if __name__ == "__main__":
    institution = InstitutionClient()

