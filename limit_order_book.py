# Price time priority limit order book
# LOB = limit order book
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
        # TODO: REPLICATE THIS
        self.bids = []
        self.asks = []
        heapq.heapify(self.bids)
        heapq.heapify(self.asks)

    def add_order(self, side, price, quantity, user):
        order = Order(user, price, quantity, datetime.now())
        if side == 'bid':
            # highest bid to the top: sorts by price then timestamp
            heapq.heappush(self.bids, (-price, order.timestamp, order)) 
        elif side == 'ask':
            # lowest ask to the top
            heapq.heappush(self.asks, (price, order.timestamp, order))
        self.match_orders()
        self.display()

    def cancel_order(self, side, price, user):
        if side == 'bid':
            target_book = self.bids
        elif side == 'ask':
            target_book = self.asks
        cancelled = False 
        # Albert: note that this cancels all orders in a price level for a user, not canceling a specific order because we don't have order-ids. I think this is fine
        # Albert: i think we do cancel all those orders successfully. I think this behavior is okay.
        i = 0
        while i < len(target_book): 
            if target_book[i][2].price == price and target_book[i][2].user == user:
                del target_book[i]
                heapq.heapify(target_book)
                cancelled = True
                i = 0  
            else:
                i += 1
        self.display()
        return cancelled

    # TODO: ALBERT says that he thinks this function works except for when users can't afford to buy or sell (insufficient stock or money). To fix this, Albert thinks easiest way is to just not bother checking for this. Like allow people to have negative amounts of balance/money and stock. That is the simplest solution, we can justify this by saying having negative amounts of balance/money and stock is just"shorting". SO u can kind of ignore the later TODOs in this function. 
    # the margin/shorting system i propose is 0 interest, loans are settled at time = infinity, so it's a "valid" margin/shorting system
    # TODO If we want, we can allow shorting/negative amounts of stock or money (negative money is like margin/borrowing money). But, I didn't allow shorting or margin because IMO this is more realistic for a simple stock exchange (in practice, margin and shorting is complicated). Prevent orders from being executed if a user does not have enough money to buy the stock or enough stock to sell. also check multiple order levels to see if the order can be filled and execute all crossing levels
    def match_orders(self):
        """Prevent orders from being executed if a user does not have enough money to buy the stock or enough stock to sell. also check multiple order levels to see if the order can be filled and execute all crossing levels"""
        # If the top bid and ask are not enough to fill the order size, we need to loop at look at the next highest bid or next lowest ask and see if those cross the order price, until we fill the entire order size or the bids or asks no longer cross. TODO: check that this works correctly
        while self.bids and self.asks:
            bid = self.bids[0][2]
            ask = self.asks[0][2]

            if -self.bids[0][0] >= self.asks[0][0]:  # Check if top bid price is >= top ask price
                executed_quantity = min(bid.quantity, ask.quantity)
                execution_price = (bid.price + ask.price) / 2

                # Check if users have enough balance and stocks for the transaction
                if bid.user.balance < executed_quantity * execution_price or ask.user.stocks < executed_quantity:
                    # TODO: better error handling? what do we do with the order that was not executed?
                    print("Error: User does not have enough balance or stocks to execute order.")
                    break
                # TODO - should we just allow shorting/negative amounts of stock or money because then we don't have to worry about this?
                
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

                """
                print(f"\nOrder executed: {executed_quantity} shares at ${execution_price:.2f}")
                print(f"{bid.user.username} new balance: ${bid.user.balance:.2f}, stocks: {bid.user.stocks}")
                print(f"{ask.user.username} new balance: ${ask.user.balance:.2f}, stocks: {ask.user.stocks}")
                """

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
        # TODO: Add ability to Configure this in UI 
        self.balance = 1000
        self.stocks = 100

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
            user = authenticate(users, username, password)
            if user:
                logged_in_UI(user, username, book)

        elif option == '2':
            username = input("Enter your username: ")
            password = input("Enter your password: ")
            user = authenticate(users, username, password)

            if user:
                logged_in_UI(user, username, book)

            else:
                print("Invalid username or password. Try again.")

        elif option == '3':
            book.display()

        elif option == '4':
            break

        else:
            print("Invalid option. Try again.")
            

def logged_in_UI(user, username, book):
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


def test_add_order():
    # Test adding bid and ask orders and check if they are stored correctly in the order book
    book = LimitOrderBook()
    user1 = User("user1", "password1")
    user2 = User("user2", "password2")

    book.add_order("bid", 10, 5, user1)
    assert len(book.bids) == 1, "Failed to add bid order to order book"

    book.add_order("ask", 12, 3, user2)
    assert len(book.asks) == 1, "Failed to add ask order to order book"

    book.add_order("bid", 9, 7, user1)
    assert len(book.bids) == 2, "Failed to add multiple bid orders to order book"

    book.add_order("ask", 15, 2, user2)
    assert len(book.asks) == 2, "Failed to add multiple ask orders to order book"

    assert book.bids[0][2].price == 10, "Incorrect bid order price"
    assert book.bids[0][2].quantity == 5, "Incorrect bid order quantity"
    assert book.bids[0][2].user == user1, "Incorrect bid order user"

    assert book.asks[0][2].price == 12, "Incorrect ask order price"
    assert book.asks[0][2].quantity == 3, "Incorrect ask order quantity"
    assert book.asks[0][2].user == user2, "Incorrect ask order user"

def test_cancel_order():
    # Test canceling bid and ask orders and check if they are removed from the order book
    book = LimitOrderBook()
    user1 = User("user1", "password1")
    user2 = User("user2", "password2")

    book.add_order("bid", 10, 5, user1)
    book.add_order("ask", 12, 3, user2)

    assert book.cancel_order("bid", 10, user1) == True, "Failed to cancel bid order"
    assert len(book.bids) == 0, "Bid order not removed from order book"

    assert book.cancel_order("ask", 12, user2) == True, "Failed to cancel ask order"
    assert len(book.asks) == 0, "Ask order not removed from order book"

    assert book.cancel_order("bid", 10, user1) == False, "Incorrectly canceled non-existing bid order"
    assert book.cancel_order("ask", 12, user2) == False, "Incorrectly canceled non-existing ask order"

def test_match_orders():
    # Test order matching and execution with different scenarios
    book = LimitOrderBook()
    user1 = User("user1", "password1")
    user2 = User("user2", "password2")

    # Scenario 1: Exact match between bid and ask
    book.add_order("bid", 10, 5, user1)
    book.add_order("ask", 10, 5, user2)

    assert len(book.bids) == 0, "Failed to clear bid order book after execution"
    assert len(book.asks) == 0, "Failed to clear ask order book after execution"
    assert user1.balance == 950, "Incorrect user1 balance after execution"
    assert user1.stocks == 105, "Incorrect user1 stocks after execution"
    assert user2


if __name__ == "__main__":
    test_add_order()
    test_cancel_order()
    test_match_orders()
    
    main()