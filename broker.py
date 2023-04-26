import socket, threading, time, grpc, os
import exchange_pb2
from exchange_pb2_grpc import BrokerServiceServicer, BrokerServiceStub, add_BrokerServiceServicer_to_server
from helpers import Constants as c
from helpers import TwoFaultStub
from typing import Dict, List, Tuple, Set
from concurrent import futures

FEE = 1

class Broker(BrokerServiceServicer):
    def __init__(self) -> None:
        self.uid_to_balance: Dict[str, int] = {}
        self.uid_to_tickers_to_amounts: Dict[str, List[Tuple[str, int]]] = {}
        self.uid_to_oids: Dict[int, Set[int]] = {} # user id to order ids
        self.broker_balance = 10000 # the broker has $100 (10k cents) to cover fees
        self.held_stocks = []
        self.stub = TwoFaultStub()
        self.stub.connect()

    def DepositCash(self, request, context):
        if request.uid not in self.uid_to_balance.keys():
            # just return empty regardless; non-compliant client
            return exchange_pb2.Empty()
        self.uid_to_balance[request.uid] += request.amount
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

        result = self.stub.stub.CancelOrder(request.oid)

        if result.result:
            self.uid_to_oids[request.uid].remove(request.oid)

        return result

    def handle_bid(self, request):
        if request.uid not in self.uid_to_balance.keys():
            return exchange_pb2.OrderId(oid=-1)

        balance = self.uid_to_balance[request.uid]

        # Note that all costs are in cents
        cost = request.price * request.quantity

        if cost + FEE > balance:
            return exchange_pb2.OrderId(oid=-1)

        response = self.stub.stub.SendOrder(request=request)

        if response.oid == -1:
            # don't charge the cost if the order doesn't go through, only fee
            self.uid_to_balance[request.uid] -= FEE
            return exchange_pb2.OrderId(oid=-1)

        self.uid_to_balance[request.uid] -= cost + FEE
        self.broker_balance += FEE - c.EXCHANGE_FEE
        self.uid_to_oids[request.uid].add(response.oid)

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
        response = self.stub.stub.SendOrder(request=request)

        self.uid_to_balance[request.uid] -= FEE
        self.broker_balance += FEE - c.EXCHANGE_FEE
        self.uid_to_oids[request.uid].add(response.oid)

        if response.oid == -1:
            return exchange_pb2.OrderId(oid=-1)
        
        self.uid_to_tickers_to_amounts[request.uid][request.ticker] -= quantity_owned

        return exchange_pb2.OrderId(oid=response.oid)
    
    def receive_pings(self):
        while True:
            self.stub.Ping(exchange_pb2.Empty())
            time.sleep(3)
    

if __name__ == "__main__":
    broker = Broker()
    threading.Thread(target=broker.receive_pings).start()
