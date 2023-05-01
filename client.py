import socket, threading, time, grpc, os
import exchange_pb2
from exchange_pb2_grpc import BrokerServiceStub
from constants import SERVER_IPS, HEARTRATE, NUM_SERVERS, CONNECTION_WAIT_TIME, MAX_VOTE_ATTEMPTS, BACKGROUND_STUB_REFRESH_RATE, EXCHANGE_FEE, LOG_DIR, PKL_DIR, USER_KEYS, DIVIDER, TICKERS
from typing import Dict, List, Tuple, Set, Optional
from concurrent import futures

class BrokerClient():
    def __init__(self):
        server_address = 'localhost:50051'  # Replace with the actual server address and port
        channel = grpc.insecure_channel(server_address)
        self.stub = BrokerServiceStub(channel)
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

import tkinter as tk
from tkinter import ttk

class BrokerClientUI(tk.Tk):
    def __init__(self, broker_client):
        super().__init__()
        self.broker_client = broker_client
        self.title("Broker Client")
        self.geometry("600x400")

        self.create_widgets()

    def create_widgets(self):
        self.register_frame = ttk.LabelFrame(self, text="Register")
        self.register_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.uid_label = ttk.Label(self.register_frame, text="UID:")
        self.uid_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.uid_entry = ttk.Entry(self.register_frame)
        self.uid_entry.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        self.register_button = ttk.Button(self.register_frame, text="Register", command=self.register)
        self.register_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        self.deposit_cash_frame = ttk.LabelFrame(self, text="Deposit Cash")
        self.deposit_cash_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.amount_label = ttk.Label(self.deposit_cash_frame, text="Amount:")
        self.amount_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.amount_entry = ttk.Entry(self.deposit_cash_frame)
        self.amount_entry.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        self.deposit_cash_button = ttk.Button(self.deposit_cash_frame, text="Deposit Cash", command=self.deposit_cash)
        self.deposit_cash_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        self.order_frame = ttk.LabelFrame(self, text="Send Order")
        self.order_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        self.order_type_label = ttk.Label(self.order_frame, text="Order Type (BID/ASK):")
        self.order_type_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.order_type_entry = ttk.Entry(self.order_frame)
        self.order_type_entry.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        self.ticker_label = ttk.Label(self.order_frame, text="Ticker:")
        self.ticker_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.ticker_entry = ttk.Entry(self.order_frame)
        self.ticker_entry.grid(row=1, column=1, padx=5, pady=5, sticky="e")

        self.quantity_label = ttk.Label(self.order_frame, text="Quantity:")
        self.quantity_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.quantity_entry = ttk.Entry(self.order_frame)
        self.quantity_entry.grid(row=2, column=1, padx=5, pady=5, sticky="e")
        self.price_label = ttk.Label(self.order_frame, text="Price:")
        self.price_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.price_entry = ttk.Entry(self.order_frame)
        self.price_entry.grid(row=3, column=1, padx=5, pady=5, sticky="e")

        self.send_order_button = ttk.Button(self.order_frame, text="Send Order", command=self.send_order)
        self.send_order_button.grid(row=4, column=0, columnspan=2, padx=5, pady=5)

        self.cancel_order_frame = ttk.LabelFrame(self, text="Cancel Order")
        self.cancel_order_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

        self.oid_label = ttk.Label(self.cancel_order_frame, text="Order ID:")
        self.oid_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.oid_entry = ttk.Entry(self.cancel_order_frame)
        self.oid_entry.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        self.cancel_order_button = ttk.Button(self.cancel_order_frame, text="Cancel Order", command=self.cancel_order)
        self.cancel_order_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

    def register(self):
        uid = int(self.uid_entry.get())
        self.broker_client.Register(uid)

    def deposit_cash(self):
        amount = float(self.amount_entry.get())
        self.broker_client.DepositCash(amount)

    def send_order(self):
        order_type = exchange_pb2.OrderType.BID if self.order_type_entry.get().upper() == "BID" else exchange_pb2.OrderType.ASK
        ticker = self.ticker_entry.get()
        quantity = int(self.quantity_entry.get())
        price = float(self.price_entry.get())
        self.broker_client.SendOrder(order_type, ticker, quantity, price, self.broker_client.uid)

    def cancel_order(self):
        oid = int(self.oid_entry.get())
        self.broker_client.CancelOrder(oid)

if __name__ == "__main__":
    broker_client = BrokerClient()
    app = BrokerClientUI(broker_client)
    app.mainloop()