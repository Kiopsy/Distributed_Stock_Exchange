import socket, threading, time, grpc, os
import exchange_pb2
from exchange_pb2_grpc import BrokerServiceStub
import constants as c
from typing import Dict, List, Tuple, Set, Optional
from concurrent import futures
from tkinter import PhotoImage
import pickle

class BrokerClient():
    def __init__(self, channel):
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

# if __name__ == "__main__":
#     channel = grpc.insecure_channel(c.BROKER_IP[1] + ':' + str(c.BROKER_IP[0]))
#     client = BrokerClient(channel)
#     while True:
#         print("[1] Register\n[2] Buy/Sell\n[3] Deposit Cash\n[4] Get Stocks")
#         inp = input("> ")
#         if inp == '1':
#             print("What uid?")
#             uid = input("> ")
#             client.Register(uid)
#         elif inp == '2':
#             client.make_order()
#         elif inp == '3':
#             print("How much?")
#             amount = input("> ")
#             client.DepositCash(int(amount))
#         else:
#             err, success, stocks = client.GetStocks()
#             if not success:
#                 print(err)
#             else:
#                 for key, value in stocks.items():
#                     print(f"{key}: {value}")

import tkinter as tk
from tkinter import messagebox
"""
class BrokerClientUI(tk.Tk):
    def __init__(self, broker_client):
        super().__init__()
        self.title("Broker Client")
        self.geometry("400x300")
        self.broker_client = broker_client

        self.create_widgets()
                    
    def create_widgets(self):
        self.logo_image = PhotoImage(file="logo.png")
        self.logo_image = self.logo_image.subsample(2, 2)  # Adjust the numbers (2, 2) to resize the logo
        self.logo_label = tk.Label(self, image=self.logo_image)
        self.logo_label.grid(row=0, column=0, columnspan=2)

        self.uid_label = tk.Label(self, text="User ID:")
        self.uid_entry = tk.Entry(self)
        self.uid_label.grid(row=1, column=0)
        self.uid_entry.grid(row=1, column=1)

        self.register_button = tk.Button(self, text="Register", command=self.register)
        self.register_button.grid(row=2, column=0, columnspan=2)

        self.registration_status = tk.Label(self, text="")
        self.registration_status.grid(row=3, column=0, columnspan=2)

        self.action_label = tk.Label(self, text="Action:")
        self.action_var = tk.StringVar(self)
        self.action_var.set("Buy")
        self.action_dropdown = tk.OptionMenu(self, self.action_var, "Buy", "Sell")
        self.action_dropdown.grid(row=4, column=1)

        self.ticker_label = tk.Label(self, text="Ticker:")
        self.ticker_entry = tk.Entry(self)
        self.ticker_label.grid(row=5, column=0)
        self.ticker_entry.grid(row=5, column=1)

        self.quantity_label = tk.Label(self, text="Quantity:")
        self.quantity_entry = tk.Entry(self)
        self.quantity_label.grid(row=6, column=0)
        self.quantity_entry.grid(row=6, column=1)

        self.price_label = tk.Label(self, text="Price:")
        self.price_entry = tk.Entry(self)
        self.price_label.grid(row=7, column=0)
        self.price_entry.grid(row=7, column=1)

        self.submit_order_button = tk.Button(self, text="Submit Order", command=self.submit_order)
        self.submit_order_button.grid(row=8, column=0, columnspan=2)

        self.deposit_label = tk.Label(self, text="Deposit Cash:")
        self.deposit_entry = tk.Entry(self)
        self.deposit_label.grid(row=9, column=0)
        self.deposit_entry.grid(row=9, column=1)

        self.deposit_button = tk.Button(self, text="Deposit", command=self.deposit_cash)
        self.deposit_button.grid(row=10, column=0, columnspan=2)

        self.deposit_status = tk.Label(self, text="")
        self.deposit_status.grid(row=11, column=0, columnspan=2)

        self.deposit_status = tk.Label(self, text="")
        self.deposit_status.grid(row=12, column=0, columnspan=2)

        self.cancel_label = tk.Label(self, text="Cancel Order ID:")
        self.cancel_entry = tk.Entry(self)
        self.cancel_label.grid(row=13, column=0)
        self.cancel_entry.grid(row=13, column=1)

        self.cancel_button = tk.Button(self, text="Cancel Order", command=self.cancel_order)
        self.cancel_button.grid(row=14, column=0, columnspan=2)

        self.cancel_status = tk.Label(self, text="")
        self.cancel_status.grid(row=15, column=0, columnspan=2)

    def cancel_order(self):
        oid = self.cancel_entry.get()
        try:
            self.broker_client.CancelOrder(int(oid))
            self.cancel_status.config(text="Cancel request sent", fg="green")
        except ValueError:
            messagebox.showerror("Error", "Invalid input; please enter a valid order ID.")


    def register(self):
        uid = self.uid_entry.get()
        self.broker_client.Register(uid)
        if self.broker_client.uid:
            self.registration_status.config(text="Successfully registered", fg="green")
        else:
            self.registration_status.config(text="Error while registering", fg="red")

    def submit_order(self):
        order_type = self.action_var.get()
        ticker = self.ticker_entry.get()
        quantity = self.quantity_entry.get()
        price = self.price_entry.get()

        if order_type == "Buy":
            order_type = exchange_pb2.OrderType.BID
        else:
            order_type = exchange_pb2.OrderType.ASK

        try:
            self.broker_client.SendOrder(order_type, ticker, int(quantity), int(price), self.broker_client.uid)
        except ValueError:
            messagebox.showerror("Error", "Invalid, make sure all fields are filled with valid values.")

    def deposit_cash(self):
        amount = self.deposit_entry.get()
        try:
            success = self.broker_client.DepositCash(int(amount))
            if success:
                self.deposit_status.config(text="Deposit successful", fg="green")
            else:
                self.deposit_status.config(text="Deposit failed", fg="red")
        except ValueError:
            messagebox.showerror("Error", "Invalid input; please enter a valid amount.")

def main():
    channel = grpc.insecure_channel(c.BROKER_IP[1] + ':' + str(c.BROKER_IP[0]))
    client = BrokerClient(channel)
    app = BrokerClientUI(client)
    app.mainloop()

main()
"""