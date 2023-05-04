from client import BrokerClient
import socket, threading, time, grpc, os
import exchange_pb2
from exchange_pb2_grpc import BrokerServiceStub
import constants as c
from typing import Dict, List, Tuple, Set, Optional
from concurrent import futures
import grpc
import constants as c
import time
import random

class SimpleTradingBot:
    def __init__(self, client):
        self.client = client
        self.uid = random.randint(0, 1000000) # Set user ID here, here we choose random integer
        self.client.Register(self.uid)
        self.client.DepositCash(self.uid, 10000000)  
        self.ticker = "AAPL"  # Set the stock ticker for trading
        self.martingale_base_order_size = 1
        self.martingale_multiplier = 2
        self.martingale_current_order_size = self.martingale_base_order_size
        self.grid_spacing = 0.5  # Set the grid spacing in percentage
        self.grid_order_size = 
    def buy_stock(self, ticker, quantity, price):
        order_type = exchange_pb2.OrderType.BID
        self.client.SendOrder(order_type, ticker, quantity, int(price), self.uid)
        print(f"Sent request of buying {quantity} shares of {ticker} at ${price}")
    def sell_stock(self, ticker, quantity, price):
        order_type = exchange_pb2.OrderType.ASK
        self.client.SendOrder(order_type, ticker, quantity, int(price), self.uid)
        print(f"Sent request of selling {quantity} shares of {ticker} at ${price}")
    def get_balance(self):
        return self.client.GetBalance(self.uid)

    def get_stocks(self):
        _, success, stocks = self.client.GetStocks(self.uid)
        if success:
            return stocks
        else:
            return None
    def get_stock_price(self, ticker):
        pass
    def martingale_strategy(self):
        current_price = self.get_stock_price(self.ticker)
        if current_price is None:
            return
        self.buy_stock(self.ticker, self.martingale_current_order_size, current_price)
        if current_price > self.previous_price:
            self.sell_stock(self.ticker, self.martingale_current_order_size, current_price)
            self.martingale_current_order_size = self.martingale_base_order_size
        else:
            # If the price goes down, double the order size for the next trade
            self.martingale_current_order_size *= self.martingale_multiplier
        self.previous_price = current_price

    def grid_trading_strategy(self):
        current_price = self.get_stock_price(self.ticker)
        if current_price is None:
            return

        grid_levels = self.calculate_grid_levels(current_price)

        for level in grid_levels:
            if level["type"] == "buy" and current_price <= level["price"]:
                self.buy_stock(self.ticker, self.grid_order_size, level["price"])
            elif level["type"] == "sell" and current_price >= level["price"]:
                self.sell_stock(self.ticker, self.grid_order_size, level["price"])

    def calculate_grid_levels(self, current_price):
        levels = []
        for i in range(1, 11):
            buy_price = current_price * (1 - (self.grid_spacing / 100) * i)
            sell_price = current_price * (1 + (self.grid_spacing / 100) * i)
            levels.append({"type": "buy", "price": buy_price})
            levels.append({"type": "buy", "price": buy_price})
            levels.append({"type": "sell", "price": sell_price})
        return levels
    def all_trading_strategy(self):
        # Choose the strategy to use
        strategy_choice = random.choice(["martingale", "grid_trading", "moving_average_crossover"])
        if strategy_choice == "martingale":
            self.martingale_strategy()
        elif strategy_choice == "grid_trading":
            self.grid_trading_strategy()
        elif strategy_choice == "moving_average_crossover":
            self.moving_average_crossover_strategy()

    def continuous_trading(self): # for throughpu test
        tickers = ['AAPL', 'GOOGL', 'MSFT']
        ticker = random.choice(tickers)
        quantity = random.randint(1, 10)
        price = round(random.uniform(50, 1000), 2)
        action = random.choice(['buy', 'sell'])
        if action == 'buy':
            self.buy_stock(ticker, quantity, price)
        elif action == 'sell':
            self.sell_stock(ticker, quantity, price)
    def run(self):
        while True:
            self.continuous_trading()
            time.sleep(0.1)  # Sleep for 0.5 seconds before running the strategy again




            
def main():
    channel = grpc.insecure_channel(c.BROKER_IP[1] + ':' + str(c.BROKER_IP[0]))
    client = BrokerClient(channel)
    bot = SimpleTradingBot(client)
    try:
        bot.run()
    except AttributeError as e:
        print("An error occurred:", e)

if __name__ == "__main__":
    main()
