import heapq
from collections import deque

class Order:
    def __init__(self, price, quantity, timestamp):
        self.price = price
        self.quantity = quantity
        self.timestamp = timestamp

class LimitOrderBook:
    def __init__(self):
        self.bids = []
        self.asks = []
        heapq.heapify(self.bids)
        heapq.heapify(self.asks)

    def add_order(self, side, price, quantity, timestamp):
        order = Order(price, quantity, timestamp)
        if side == 'bid':
            heapq.heappush(self.bids, (-price, timestamp, order))
        elif side == 'ask':
            heapq.heappush(self.asks, (price, timestamp, order))

    def cancel_order(self, side, price, timestamp):
        if side == 'bid':
            target_book = self.bids
        elif side == 'ask':
            target_book = self.asks

        for i in range(len(target_book)):
            if target_book[i][1] == timestamp and target_book[i][2].price == price:
                del target_book[i]
                heapq.heapify(target_book)
                return True
        return False

    def display(self):
        print("Bids:")
        for bid in self.bids:
            print(f"Price: {bid[2].price}, Quantity: {bid[2].quantity}, Timestamp: {bid[1]}")
        print("\nAsks:")
        for ask in self.asks:
            print(f"Price: {ask[2].price}, Quantity: {ask[2].quantity}, Timestamp: {ask[1]}")

def main():
    book = LimitOrderBook()

    while True:
        print("\nOptions:")
        print("1. Add order")
        print("2. Cancel order")
        print("3. Display order book")
        print("4. Quit")

        option = input("Select an option: ")

        if option == '1':
            side = input("Enter 'bid' or 'ask': ")
            price = float(input("Enter price: "))
            quantity = int(input("Enter quantity: "))
            timestamp = int(input("Enter timestamp: "))
            book.add_order(side, price, quantity, timestamp)

        elif option == '2':
            side = input("Enter 'bid' or 'ask': ")
            price = float(input("Enter price: "))
            timestamp = int(input("Enter timestamp: "))
            if book.cancel_order(side, price, timestamp):
                print("Order cancelled.")
            else:
                print("Order not found.")

        elif option == '3':
            book.display()

        elif option == '4':
            break

        else:
            print("Invalid option. Try again.")

if __name__ == "__main__":
    main()
