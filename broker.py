import socket, threading, time, grpc, os
import exchange_pb2
from exchange_pb2_grpc import BrokerServiceServicer, add_BrokerServiceServicer_to_server
import constants as c
from helpers import nFaultStub
from typing import Dict, List, Tuple, Set, Deque, Any
from concurrent import futures
from collections import deque
import exchange_pb2_grpc
import pickle

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
        self.oids: Set[int] = {}
        self.ticker_balances: Dict[str, int] = {}
        self.fills: Deque[Tuple[int, int, int]] = deque()

class Broker(BrokerServiceServicer):
    def __init__(self) -> None:
        self.uid = c.BROKER_KEYS[0]
        self.uid_to_user: Dict[int, User] = {}
        self.oid_to_order: Dict[int, Order] = {}

        self.broker_balance = 10_000 # the broker has $100 (10k cents) to cover fee
        self.held_stocks = []
        
        self.stub = nFaultStub()
        if self.stub.connect():
            self.stub.backup_stub_connect_thread.start()
    
    def sprint(self, *args, **kwargs):
        print("Broker:", *args, **kwargs)

    def Register(self, request, context):
        if request.uid in self.uid_to_user.keys():
            return exchange_pb2.Result(result=False)

        self.uid_to_user[request.uid] = User(request.uid)

        self.sprint(f"Registered user id {request.uid}")

        return exchange_pb2.Result(result=True)

    def DepositCash(self, request, context):
        if request.uid not in self.uid_to_user.keys():
            # just return empty regardless; non-compliant client
            return exchange_pb2.Empty()

        self.uid_to_user[request.uid].balance += request.amount
        # Deposit enough cash with exchange to cover any user transactions
        self.stub.DepositCash(exchange_pb2.Deposit(uid=self.uid, amount=request.amount))
        self.sprint(f"User id {request.uid} has deposited {request.amount} dollars")
        return exchange_pb2.Empty()
    
    def GetOrderList(self, request, context):
        return self.stub.GetOrderList(request)

    def SendOrder(self, request, context):
        if request.type == exchange_pb2.OrderType.BID:
            return self.handle_bid(request)
        else:
            return self.handle_ask(request)

    def GetStocks(self, request, context):
        if request.uid not in self.uid_to_user.keys():
            return exchange_pb2.UserStocks(bytes())

        stocks_bytes = pickle.dumps(self.uid_to_user[request.uid].ticker_balances)

        return exchange_pb2.UserStocks(pickle=stocks_bytes)
    
    def GetBalance(self, request, context):
        if request.uid not in self.uid_to_user.keys():
            return exchange_pb2.Balance(balance=-1)
        balance = self.uid_to_user[request.uid].balance
        print(f"User id {request.uid} has balance {balance}")
        return exchange_pb2.Balance(balance=balance)

    def CancelOrder(self, request, context):
        if request.uid not in self.uid_to_user.keys():
            return exchange_pb2.Result(result=False)

        if request.oid not in self.oid_to_order.keys():
            return exchange_pb2.Result(result=False)

        self.sprint(f"User id {request.uid} is attempting to cancel {request.oid}")
        result = self.stub.CancelOrder(exchange_pb2.OrderId(oid=request.oid))

        if result.result:
            order = self.oid_to_order[request.oid]
            if order.side == exchange_pb2.OrderType.BID:
                self.uid_to_user[request.uid].balance += order.price * order.amount
            else:
                self.uid_to_user[request.uid].ticker_balances[order.ticker] += order.amount
            self.sprint(f"User id {request.uid} cancelled {request.oid}")

        return result
    
    def OrderFill(self, request, context):
        if request.uid not in self.uid_to_user.keys():
            return exchange_pb2.FillInfo(oid=-1, amount_filled=-1)

        if len(self.uid_to_user[request.uid].fills) == 0:
            return exchange_pb2.FillInfo(oid=-1, amount_filled=-1)

        oid, amount_filled, execution_price = self.uid_to_user[request.uid].fills.popleft()

        side = self.oid_to_order[oid].side
        ticker = self.oid_to_order[oid].ticker

        self.sprint(f"User id {request.uid} had a filled order sent")
        return exchange_pb2.BrokerFillInfo(oid=oid, amount_filled=amount_filled, ticker=ticker,
                                           execution_price=execution_price, order_type=side)

    def handle_bid(self, request):
        if request.uid not in self.uid_to_user.keys():
            return exchange_pb2.OrderId(oid=-1)
        
        self.sprint(f"Handling bid for User id {request.uid}")
        balance = self.uid_to_user[request.uid].balance

        # Note that all costs are in cents
        cost = request.price * request.quantity


        if cost + c.BROKER_FEE > balance:
            return exchange_pb2.OrderId(oid=-1)

        request_uid = request.uid
        request.uid = self.uid
        response = self.stub.SendOrder(request=request)

        if not response:
            self.sprint("Error communicating with exchange ")
            return exchange_pb2.OrderId(oid=-1)

        if response.oid == -1:
            # don't charge the cost if the order doesn't go through, only fee
            self.uid_to_user[request.uid].balance -= c.BROKER_FEE
            return exchange_pb2.OrderId(oid=-1)

        self.uid_to_user[request_uid].balance -= cost + c.BROKER_FEE
        self.broker_balance += c.BROKER_FEE - c.EXCHANGE_FEE
        self.oid_to_order[response.oid] = Order(response.oid, 
                                                request_uid,
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
        
        self.sprint(f"Asked ticker: {request.ticker}")

        if request.quantity <= 0:
            return exchange_pb2.OrderId(oid=-1)

        quantity_owned = self.uid_to_user[request.uid].ticker_balances.get(request.ticker, 0)
        
        if request.quantity > quantity_owned:
            self.sprint(f"User doesn't have enough owned, only owns {quantity_owned}, aborting")
            return exchange_pb2.OrderId(oid=-1)

        # Send order to the exchange. Once the order is queued,
        # remove the stocks and charge a fee from the user's account
        request_uid = request.uid
        request.uid = self.uid
        response = self.stub.SendOrder(request=request)

        if response.oid == -1:
            self.sprint("Exchange returns -1")
            return exchange_pb2.OrderId(oid=-1)

        self.uid_to_user[request_uid].balance -= c.BROKER_FEE
        self.broker_balance += c.BROKER_FEE - c.EXCHANGE_FEE
        self.oid_to_order[response.oid] = Order(response.oid,
                                                request_uid,
                                                request.quantity,
                                                request.ticker,
                                                request.price,
                                                exchange_pb2.OrderType.ASK)
        
        self.uid_to_user[request_uid].ticker_balances[request.ticker] -= request.quantity
        return exchange_pb2.OrderId(oid=response.oid)

    def receive_fills(self):
        self.sprint("Receive fills thread started")
        while True:
            fill = self.stub.OrderFill(exchange_pb2.UserInfo(uid=self.uid))
            if not fill:
                time.sleep(1)
                continue
            if fill.oid == -1:
                # self.sprint("Received no fill")
                time.sleep(0.2) # invalid order
                continue
            self.sprint(f"Received a fill with oid {fill.oid}")
            order = self.oid_to_order[fill.oid]
            fill.amount_filled = int(fill.amount_filled)
            self.uid_to_user[order.uid].fills.append((order.oid, fill.amount_filled, fill.execution_price))
            self.oid_to_order[fill.oid].amount -= fill.amount_filled
            if order.side == exchange_pb2.OrderType.BID:
                shares = self.uid_to_user[order.uid].ticker_balances.get(order.ticker, 0)
                self.uid_to_user[order.uid].ticker_balances[order.ticker] = shares + fill.amount_filled
            else:
                self.uid_to_user[order.uid].balance += fill.amount_filled * fill.execution_price

            self.sprint(f"User id {order.uid} had a filled order")

            time.sleep(.1) # latency?

def setup() -> Tuple[Broker, Any]:
    broker = Broker()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_BrokerServiceServicer_to_server(broker, server)
    ip_port = c.BROKER_IP[1] + ':' + str(c.BROKER_IP[0])
    print(f"Starting broker at {ip_port}")
    server.add_insecure_port(ip_port)
    server.start()
    t = threading.Thread(target=broker.receive_fills)
    t.daemon = True
    t.start()
    return (broker, server)

if __name__ == "__main__":
    broker, server = setup()
    print(f"Broker server initialized at {c.BROKER_IP[1]} on port {c.BROKER_IP[0]}")
    server.wait_for_termination()
