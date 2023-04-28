import socket, threading, time, grpc, os
import exchange_pb2
from exchange_pb2_grpc import BrokerServiceServicer, add_BrokerServiceServicer_to_server
import constants as c
from helpers import nFaultStub
from typing import Dict, List, Tuple, Set, Deque
from concurrent import futures
from collections import deque
import exchange_pb2_grpc

FEE = 1

class Broker(BrokerServiceServicer):
    def __init__(self) -> None:
        self.uid = c.USER_KEYS[0]
        self.uid_to_balance: Dict[int, int] = {}
        self.uid_to_tickers_to_amounts: Dict[int, List[Tuple[str, int]]] = {}
        self.uid_to_oids: Dict[int, Set[int]] = {} # user id to order ids
        self.oid_to_uid: Dict[int, int] = {}
        self.uid_to_fills: Dict[int, Deque[Tuple[int, int]]] = {}

        self.broker_balance = 10000 # the broker has $100 (10k cents) to cover fees
        self.held_stocks = []
        
        self.stub = nFaultStub()
        if self.stub.connect():
            self.stub.backup_stub_connect_thread.start()
        
    def Register(self, request, context):
        if request.uid in self.uid_to_balance.keys():
            return exchange_pb2.Result(result=False)
        
        self.uid_to_balance.update(request.uid, 0)
        self.uid_to_oids.update(request.uid, set())
        self.uid_to_tickers_to_amounts.update(request.uid, [])
        self.uid_to_fills.update(request.uid, deque())

        return exchange_pb2.Result(result=True)

    def DepositCash(self, request, context):
        if request.uid not in self.uid_to_balance.keys():
            # just return empty regardless; non-compliant client
            return exchange_pb2.Empty()
        self.uid_to_balance[request.uid] += request.amount
        # Deposit enough cash with exchange to cover any user transactions
        self.stub.DepositCash(request.amount)
        return exchange_pb2.Empty()

    def SendOrder(self, request, context):
        if request.OrderType == exchange_pb2.OrderType.BID:
            return self.handle_bid(request)
        else:
            return self.handle_offer(request)

    def CancelOrder(self, request, context):
        if request.uid not in self.uid_to_oids:
            return exchange_pb2.Result(result=False)

        if request.oid not in self.uid_to_oids[request.uid]:
            return exchange_pb2.Result(result=False)

        result = self.stub.CancelOrder(request.oid)

        if result.result:
            self.uid_to_oids[request.uid].remove(request.oid)

        return result
    
    def OrderFill(self, request, context):
        if request.uid not in self.uid_to_oids:
            return exchange_pb2.FillInfo(oid=-1, amount_filled=-1)

        if len(self.uid_to_fills[request.uid]) == 0:
            return exchange_pb2.FillInfo(oid=-1, amount_filled=-1)

        oid, amount_filled = self.uid_to_fills[request.uid].popleft()

        return exchange_pb2.FillInfo(oid=oid, amount_filled=amount_filled)

    def handle_bid(self, request):
        if request.uid not in self.uid_to_balance.keys():
            return exchange_pb2.OrderId(oid=-1)

        balance = self.uid_to_balance[request.uid]

        # Note that all costs are in cents
        cost = request.price * request.quantity

        if cost + FEE > balance:
            return exchange_pb2.OrderId(oid=-1)

        response = self.stub.SendOrder(request=request)

        if response.oid == -1:
            # don't charge the cost if the order doesn't go through, only fee
            self.uid_to_balance[request.uid] -= FEE
            return exchange_pb2.OrderId(oid=-1)

        self.uid_to_balance[request.uid] -= cost + FEE
        self.broker_balance += FEE - c.EXCHANGE_FEE
        self.uid_to_oids[request.uid].add(response.oid)
        self.oid_to_uid.update(response.oid, request.uid)

        # Once we send to the exchange we want to make this oid match with whatever
        # order id the exchange gives us
        return exchange_pb2.OrderId(oid=response.oid)


    def handle_offer(self, request):
        if request.uid not in self.uid_to_positions.keys():
            return exchange_pb2.OrderId(oid=-1)
        
        if request.ticker not in self.uid_to_tickers_to_amounts[request.uid].keys():
            return exchange_pb2.OrderId(oid=-1)

        quantity_owned = self.uid_to_tickers_to_amounts[request.uid][request.ticker]
        
        if request.quantity > quantity_owned:
            return exchange_pb2.OrderId(oid=-1)
        
        # Send order to the exchange. Once the order is queued,
        # remove the stocks and charge a fee from the user's account
        response = self.stub.SendOrder(request=request)

        self.uid_to_balance[request.uid] -= FEE
        self.broker_balance += FEE - c.EXCHANGE_FEE
        self.uid_to_oids[request.uid].add(response.oid)
        self.oid_to_uid.update(response.oid, request.uid)

        if response.oid == -1:
            return exchange_pb2.OrderId(oid=-1)
        
        self.uid_to_tickers_to_amounts[request.uid][request.ticker] -= quantity_owned

        return exchange_pb2.OrderId(oid=response.oid)

    def receive_fills(self):
        while True:
            fill = self.stub.OrderFill(exchange_pb2.UserInfo(uid=self.uid))
            uid = self.oid_to_uid[fill.oid]
            self.uid_to_fills[uid].append((fill.oid, fill.amount_filled))
            # this is not done yet, need to update the rest of the maps
            time.sleep(0.1) # latency?
    

if __name__ == "__main__":
    broker = Broker()
    while True:
        _ = input("[Enter]: ")
        broker.stub.DepositCash(exchange_pb2.Deposit(uid=0, amount=100))
    # threading.Thread(target=broker.receive_fills).start()
    # deposit a dollar as a test
    # broker.stub.DepositCash(request=exchange_pb2.Deposit(uid=0, amount=100))
