import heapq
from collections import deque
from datetime import datetime

class Order:
    def __init__(self, user, price, quantity, timestamp):
        self.user = user
        self.price = price
        self.quantity = quantity
        self.timestamp = timestamp

class LimitOrderBook:
    def __init__(self):
        self.bids = []
        self.asks = []
        heapq.heapify(self.bids)
        heapq.heapify(self.asks)

    def add_order(self, side, price, quantity, user):
        order = Order(user, price, quantity, datetime.now())
        if side == 'bid':
            heapq.heappush(self.bids, (-price, order.timestamp, order))
        elif side == 'ask':
            heapq.heappush(self.asks, (price, order.timestamp, order))
        self.match_orders()
        self.display()

    def cancel_order(self, side, price, user):
        if side == 'bid':
            target_book = self.bids
        elif side == 'ask':
            target_book = self.asks

        # TODO: check that handle case where there are multiple orders at the same price from the same user - we could just cancel all those orders, check that this does that successfully
        for i in range(len(target_book)):
            if target_book[i][2].price == price and target_book[i][2].user == user:
                del target_book[i]
                heapq.heapify(target_book)
                self.display()
                return True
        return False

    # TODO - make this work correctly. Prevent orders from being executed if a user does not have enough money to buy the stock or enough stock to sell
    def match_orders(self):
        while self.bids and self.asks:
            bid = self.bids[0][2]
            ask = self.asks[0][2]

            # TODO: If the top bid and ask are not enough to fill the order size, we need to loop at look at the next highest bid or next lowest ask and see if those cross the order price, until we fill the entire order size or the bids or asks no longer cross
            if -self.bids[0][0] >= self.asks[0][0]:  # Check if top bid price is >= top ask price
                executed_quantity = min(bid.quantity, ask.quantity)
                execution_price = (bid.price + ask.price) / 2

                bid.user.balance += -executed_quantity * execution_price
                bid.user.stocks += executed_quantity
                ask.user.balance += executed_quantity * execution_price
                ask.user.stocks += -executed_quantity

                bid.quantity -= executed_quantity
                ask.quantity -= executed_quantity

                if bid.quantity == 0:
                    heapq.heappop(self.bids)
                if ask.quantity == 0:
                    heapq.heappop(self.asks)

                print(f"\nOrder executed: {executed_quantity} shares at ${execution_price:.2f}")
                print(f"{bid.user.username} new balance: ${bid.user.balance:.2f}, stocks: {bid.user.stocks}")
                print(f"{ask.user.username} new balance: ${ask.user.balance:.2f}, stocks: {ask.user.stocks}")

            else:
                break

    def display(self):
        print("Bids:")
        for bid in self.bids:
            print(f"User: {bid[2].user.username}, Price: {bid[2].price}, Quantity: {bid[2].quantity}, Timestamp: {bid[1]}")
        print("\nAsks:")
        for ask in self.asks:
            print(f"User: {ask[2].user.username}, Price: {ask[2].price}, Quantity: {ask[2].quantity}, Timestamp: {ask[1]}")

class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.balance = 1000
        self.stocks = 0

def authenticate(users, username, password):
    for user in users:
        if user.username == username and user.password == password:
            return user
    return None


def main():
    book = LimitOrderBook()
    users = []

    while True:
        print("="*20)
        print("1. Register user")
        print("2. Log in")
        print("3. Display order book")
        print("4. Quit")

        option = input("Select an option: ")
        print("="*20)

        if option == '1':
            username = input("Enter a username: ")
            password = input("Enter a password: ")
            users.append(User(username, password))
            print(f"User {username} registered.")

        elif option == '2':
            username = input("Enter your username: ")
            password = input("Enter your password: ")
            user = authenticate(users, username, password)

            if user:
                print(f"Welcome, {username}! Your balance: ${user.balance:.2f}, stocks: {user.stocks}")
                while True:
                    print("="*20)
                    print("\nUser Options:")
                    print("1. Add order")
                    print("2. Cancel order")
                    print("3. Display order book")
                    print("4. Log out")

                    user_option = input("Select an option: ")
                    print("="*20)

                    if user_option == '1':
                        side = input("Enter 'bid' or 'ask': ")
                        price = float(input("Enter price: "))
                        quantity = int(input("Enter quantity: "))
                        book.add_order(side, price, quantity, user)

                    elif user_option == '2':
                        side = input("Enter 'bid' or 'ask': ")
                        price = float(input("Enter price: "))
                        if book.cancel_order(side, price, user):
                            print("Order cancelled.")
                        else:
                            print("Order not found.")

                    elif user_option == '3':
                        book.display()

                    elif user_option == '4':
                        break

                    else:
                        print("Invalid option. Try again.")

            else:
                print("Invalid username or password. Try again.")

        elif option == '3':
            book.display()

        elif option == '4':
            break

        else:
            print("Invalid option. Try again.")

if __name__ == "__main__":
    main()
