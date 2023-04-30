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

class Order:
    def __init__(self, oid: int, uid: int, amount: int, 
                 ticker: str, price: int, side: exchange_pb2.OrderType) -> None:
        self.oid = oid
        self.uid = uid
        self.amount = amount
        self.price = price
        self.ticker = ticker
        self.side = side

class User:
    def __init__(self, uid: int) -> None:
        self.uid = uid
        self.balance = 0
        self.oids: Dict[int, Set[int]] = {}
        self.ticker_balances: Dict[str, int] = {}
        self.fills: Deque[Tuple[int, int]] = deque()

class Broker(BrokerServiceServicer):
    def __init__(self) -> None:
        self.uid = c.USER_KEYS[0]
        self.uid_to_user: Dict[int, User] = {}
        self.oid_to_order: Dict[int, Order] = {}

        self.broker_balance = 10_000 # the broker has $100 (10k cents) to cover fees
        self.held_stocks = []
        
        self.stub = nFaultStub()
        if self.stub.connect():
            self.stub.backup_stub_connect_thread.start()
        
    def Register(self, request, context):
        if request.uid in self.uid_to_user.keys():
            return exchange_pb2.Result(result=False)

        self.uid_to_user[request.uid] = User(request.uid)

        return exchange_pb2.Result(result=True)

    def DepositCash(self, request, context):
        if request.uid not in self.uid_to_user.keys():
            # just return empty regardless; non-compliant client
            return exchange_pb2.Empty()
        
        self.uid_to_user[request.uid].balance += request.amount
        # Deposit enough cash with exchange to cover any user transactions
        self.stub.DepositCash(request.amount)
        return exchange_pb2.Empty()

    def SendOrder(self, request, context):
        if request.OrderType == exchange_pb2.OrderType.BID:
            return self.handle_bid(request)
        else:
            return self.handle_ask(request)

    def CancelOrder(self, request, context):
        if request.uid not in self.uid_to_user.keys():
            return exchange_pb2.Result(result=False)

        if request.oid not in self.oid_to_order.keys():
            return exchange_pb2.Result(result=False)

        result = self.stub.CancelOrder(request.oid)

        if result.result:
            self.uid_to_user[request.uid].oids.pop(request.oid)
            order = self.oid_to_order[request.oid]
            if order.side == exchange_pb2.OrderType.BID:
                self.uid_to_user[request.uid].balance += order.price * order.amount
            else:
                self.uid_to_user[request.uid].ticker_balances[order.ticker] += order.amount

        return result
    
    def OrderFill(self, request, context):
        if request.uid not in self.uid_to_user.keys():
            return exchange_pb2.FillInfo(oid=-1, amount_filled=-1)

        if len(self.uid_to_user[request.uid].fills) == 0:
            return exchange_pb2.FillInfo(oid=-1, amount_filled=-1)

        oid, amount_filled = self.uid_to_user[request.uid].fills.popleft()

        return exchange_pb2.FillInfo(oid=oid, amount_filled=amount_filled)

    def handle_bid(self, request):
        if request.uid not in self.uid_to_user.keys():
            return exchange_pb2.OrderId(oid=-1)

        balance = self.uid_to_user[request.uid].balance

        # Note that all costs are in cents
        cost = request.price * request.quantity

        if cost + FEE > balance:
            return exchange_pb2.OrderId(oid=-1)

        response = self.stub.SendOrder(request=request)

        if response.oid == -1:
            # don't charge the cost if the order doesn't go through, only fee
            self.uid_to_user[request.uid].balance -= FEE
            return exchange_pb2.OrderId(oid=-1)

        self.uid_to_user[request.uid].balance -= cost + FEE
        self.broker_balance += FEE - c.EXCHANGE_FEE
        self.uid_to_user[request.uid].oids.add(response.oid)
        self.oid_to_order[response.oid] = Order(response.oid, 
                                                request.uid, 
                                                request.quantity,
                                                request.ticker,
                                                request.price,
                                                exchange_pb2.OrderType.BID)

        # Once we send to the exchange we want to make this oid match with whatever
        # order id the exchange gives us
        return exchange_pb2.OrderId(oid=response.oid)


    def handle_ask(self, request):
        if request.uid not in self.uid_to_user.keys():
            return exchange_pb2.OrderId(oid=-1)
        
        if request.ticker not in self.uid_to_user[request.uid].ticker_balances.keys():
            return exchange_pb2.OrderId(oid=-1)

        if request.quantity <= 0:
            return exchange_pb2.OrderId(oid=-1)

        quantity_owned = self.uid_to_user[request.uid].ticker_balances.get(request.ticker, 0)
        
        if request.quantity > quantity_owned:
            return exchange_pb2.OrderId(oid=-1)
        
        # Send order to the exchange. Once the order is queued,
        # remove the stocks and charge a fee from the user's account
        response = self.stub.SendOrder(request=request)

        self.uid_to_user[request.uid].balance -= FEE
        self.broker_balance += FEE - c.EXCHANGE_FEE
        self.uid_to_user[request.uid].oids.add(response.oid)
        self.oid_to_order[response.oid] = Order(response.oid, 
                                                request.uid, 
                                                request.ticker,
                                                request.quantity, 
                                                request.price,
                                                exchange_pb2.OrderType.ASK)

        if response.oid == -1:
            return exchange_pb2.OrderId(oid=-1)
        
        self.uid_to_user[request.uid].ticker_balances[request.ticker] -= request.quantity

        return exchange_pb2.OrderId(oid=response.oid)

    def receive_fills(self):
        while True:
            fill = self.stub.OrderFill(exchange_pb2.UserInfo(uid=self.uid))
            if fill.oid == -1:
                time.sleep(0.2)
                continue
            order = self.oid_to_order[fill.oid]
            self.uid_to_user[order.uid].fills.append((order.oid, fill.amount_filled))
            self.oid_to_order[fill.oid].amount -= fill.amount_filled
            if order.side == exchange_pb2.OrderType.BID:
                shares = self.uid_to_user[order.uid].ticker_balances.get(order.ticker, 0)
                self.uid_to_user[order.uid].ticker_balances = shares + fill.amount_filled
            else:
                self.uid_to_user[order.uid].balance += fill.amount_filled * fill.execution_price

            # No longer an active order if all shares are filled
            if self.oid_to_order[fill.oid].amount == 0:
                self.uid_to_user[order.uid].oids.pop(order.oid)

            time.sleep(0.1) # latency?
    

if __name__ == "__main__":
    broker = Broker()
    while True:
        _ = input("[Enter]: ")
        # broker.stub.DepositCash(exchange_pb2.Deposit(uid=0, amount=100))
        oid_1 = broker.stub.SendOrder(exchange_pb2.OrderInfo(ticker = "GOOGL", quantity = 10, price = 100, uid = c.USER_KEYS[0], type = exchange_pb2.OrderType.BID))
        oid_2 = broker.stub.SendOrder(exchange_pb2.OrderInfo(ticker = "GOOGL", quantity = 5, price = 100, uid = c.USER_KEYS[0], type = exchange_pb2.OrderType.ASK))
        broker.stub.CancelOrder(exchange_pb2.OrderId(oid=oid_1.oid))
        
    # threading.Thread(target=broker.receive_fills).start()
    # deposit a dollar as a test
    # broker.stub.DepositCash(request=exchange_pb2.Deposit(uid=0, amount=100))
