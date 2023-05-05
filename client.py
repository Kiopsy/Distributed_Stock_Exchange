import socket, threading, time, grpc, os
import exchange_pb2
from exchange_pb2_grpc import BrokerServiceStub
import constants as c
from typing import Dict, List, Tuple, Set, Optional
from concurrent import futures
from tkinter import PhotoImage
import pickle

class BrokerClient():
    def __init__(self):
        channel = grpc.insecure_channel(c.BROKER_IP[1] + ':' + str(c.BROKER_IP[0]))
        self.stub = BrokerServiceStub(channel)
    
    def sprint(self, *args, **kwargs):
        print("BrokerClient:", *args, **kwargs)
    
    def Register(self, uid: int) -> None:
        result = self.stub.Register(exchange_pb2.UserInfo(uid=int(uid)))
        if result.result:
            print("Successfully registered")
        else:
            print("Error while registering")
    
    def DepositCash(self, uid: int, amount: int) -> bool:
        # Deposit cash; this returns Empty
        try:
            self.stub.DepositCash(exchange_pb2.Deposit(uid=uid, amount=amount))
            return True
        except Exception as e:
            print(f"Error while depositing: {e}")
            return False
        
    def GetStocks(self, uid: int) -> Tuple[str, bool, Dict[str, int]]:
        try:
            result = self.stub.GetStocks(exchange_pb2.UserId(uid=uid))
            stocks = pickle.loads(result.pickle)
            return ("", True, stocks)
        except Exception as e:
            self.sprint(f"Error: {e}")
            return (str(e), False, {})

    def SendOrder(self, order_type, ticker, quantity, price, uid: int) -> Tuple[str, bool]:

        try:
            result = self.stub.SendOrder(exchange_pb2.OrderInfo(ticker=ticker, 
                                                                quantity=quantity,
                                                                price=price,
                                                                uid=uid,
                                                                type=order_type))
        except Exception as e:
            self.sprint(f"Error: {e}")
            result = None
        
        if result and result.oid == -1:
            res = ("Order failed!", False)
        else:
            res = (f"Order placed. Order id: {result.oid}", True)

        return res
    
    def GetBalance(self, uid: int) -> int:
        result = self.stub.GetBalance(exchange_pb2.UserId(uid=uid))
        return result.balance

    def CancelOrder(self, uid: int, oid: int) -> None:
        self.stub.CancelOrder(exchange_pb2.CancelRequest(uid=uid, oid=oid))

    def make_order(self, uid: int) -> None:
        print("Would you like to buy or sell a stock?")
        print("[1] Buy")
        print("[2] Sell")
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
        self.SendOrder(order_type, ticker, quantity, price, uid)

def setup() -> BrokerClient:
    client = BrokerClient()
    return client

if __name__ == "__main__":
    client = setup()
    uid = None
    while True:
        print("[1] Register\n[2] Buy/Sell\n[3] Deposit Cash\n[4] Get Stocks")
        inp = input("> ")
        if inp == '1':
            print("What uid?")
            uid = int(input("> "))
            client.Register(uid)
        elif not uid:
            print("Please register first.")
            continue
        if inp == '2':
            client.make_order(uid)
        elif inp == '3':
            print("How much?")
            amount = input("> ")
            client.DepositCash(uid, int(amount))
        else:
            err, success, stocks = client.GetStocks(uid)
            if not success:
                print(err)
            else:
                for key, value in stocks.items():
                    print(f"{key}: {value}")

