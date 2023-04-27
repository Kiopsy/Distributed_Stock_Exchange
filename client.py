import socket, threading, time, grpc, os
import exchange_pb2
from exchange_pb2_grpc import BrokerServiceStub
from helpers import Constants as c
from helpers import TwoFaultStub
from typing import Dict, List, Tuple, Set, Optional
from concurrent import futures

class BrokerClient():
    def __init__(self):
        self.stub = BrokerServiceStub()
        self.uid: Optional[int]
    
    def Register(self, uid) -> None:
        result = self.stub.Register(exchange_pb2.UserInfo(uid=uid))
        if result.result:
            print("Successfully registered")
            self.uid = uid
        else:
            print("Error while registering")

    
    def DepositCash(self, amount) -> None:
        if not self.uid:
            print("Please register/log in first.")
            return

        # Deposit cash; this returns Empty
        self.stub.DepositCash(exchange_pb2.Deposit(uid=self.uid, 
                                                   amount=amount))
        
    def SendOrder(self, order_type, ticker, quantity, price, uid) -> None:

        result = self.stub.SendOrder(exchange_pb2.OrderInfo(order_type=order_type,
                                                            ticker=ticker, 
                                                            quantity=quantity,
                                                            price=price,
                                                            uid=self.uid))
        if result.oid == -1:
            print("Order failed!")
        else:
            print(f"Order placed. Order id: {result.oid}")

    def CancelOrder(self, oid) -> None:
        self.stub.CancelOrder(exchange_pb2.CancelRequest(uid=self.uid, oid=oid))

if __name__ == "__main__":
    # Need this thread + another thread for receiving filled orders
    pass

# stashing code for later; ignore
def make_order() -> None:
    print("Would you like to buy or sell a stock?")
    print("[1] Buy")
    print["[2] Sell"]
    inp = input("> ")
    order_type = None
    if inp == "1":
        order_type = exchange_pb2.OrderType.BID
    elif inp == "2":
        order_type = exchange_pb2.OrderType.ASK
    else:
        print("Please enter 1 or 2.")
        return

    print("For which stock?")
    ticker = input("> ")

    print("And how many shares?")
    quantity = int(input("> "))

    print("For what price for each share?")
    price = int(input("> "))
    # send information to the broker client