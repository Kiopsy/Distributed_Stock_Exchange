# Price time priority limit order book
# LOB = limit order book
import heapq
from collections import deque
from datetime import datetime

class Order:
    def __init__(self, uid, price, quantity, timestamp, oid):
        self.uid = uid
        self.price = price
        self.quantity = quantity
        self.timestamp = timestamp
        self.oid = oid

class LimitOrderBook:
    def __init__(self, ticker = "Not set yet"):
        # self.filled_orders = deque()
        self.ticker = ticker
        self.bids = []
        self.asks = []
        heapq.heapify(self.bids)
        heapq.heapify(self.asks)

    def add_order(self, side, price, quantity, uid, new_oid):
        order = Order(uid, price, quantity, datetime.now(), new_oid)
        if side == 'bid':
            # highest bid to the top: sorts by price then timestamp
            heapq.heappush(self.bids, (-price, order.timestamp, order)) 
        elif side == 'ask':
            # lowest ask to the top
            heapq.heappush(self.asks, (price, order.timestamp, order))
        return self.match_orders()
        
        # self.display()
        # Return a list of all the matched/filled orders with the uids that were matched 

    def cancel_order_by_price(self, side, price, uid):
        if side == 'bid':
            target_book = self.bids
        elif side == 'ask':
            target_book = self.asks
        cancelled = False 
        # Albert: note that this cancels all orders in a price level for a uid, not canceling a specific order because we don't have order-ids. I think this is fine
        # Albert: i think we do cancel all those orders successfully. I think this behavior is okay.
        i = 0
        while i < len(target_book): 
            if target_book[i][2].price == price and target_book[i][2].uid == uid:
                del target_book[i]
                heapq.heapify(target_book)
                cancelled = True
                i = 0  
            else:
                i += 1
        self.display()
        return cancelled
    
    def get_orderbook(self):
        return (self.bids[:], self.asks[:])
    
    def cancel_order_by_oid(self, cancel_oid):
        did_delete = False
        
        new_bids = [] 
        # Iterate through all nodes in the heap
        while self.bids:
            bid = heapq.heappop(self.bids)
            if bid.oid != cancel_oid:
                # If the node doesn't match the 'oid', add it to the new heap
                heapq.heappush(new_bids, bid)
            else:
                did_delete = True

        # Replace the original heap with the new heap
        self.bids[:] = new_bids[:]
    
        new_asks = [] 
        # Iterate through all nodes in the heap
        while self.asks:
            ask = heapq.heappop(self.asks)
            if ask.oid != cancel_oid:
                # If the node doesn't match the 'oid', add it to the new heap
                heapq.heappush(new_asks, ask)
            else:
                did_delete = True

        # Replace the original heap with the new heap
        self.asks[:] = new_asks[:]
        
        return did_delete

    # The margin/shorting system we use is 0 interest, loans are settled at time = infinity, so it's a "valid" margin/shorting system. Allows people to have negative amounts of balance/money and stock. 
    def match_orders(self):
        """Prevent orders from being executed if a uid does not have enough money to buy the stock or enough stock to sell. also check multiple order levels to see if the order can be filled and execute all crossing levels"""
        
        filled_orders = []
        
        # If the top bid and ask are not enough to fill the order size, we need to loop at look at the next highest bid or next lowest ask and see if those cross the order price, until we fill the entire order size or the bids or asks no longer cross.
        while self.bids and self.asks:
            bid = self.bids[0][2]
            ask = self.asks[0][2]

            if -self.bids[0][0] >= self.asks[0][0]:  # Check if top bid price is >= top ask price
                executed_quantity = min(bid.quantity, ask.quantity)
                execution_price = (bid.price + ask.price) / 2

                # Albert: we do not check if users have enough balance and stocks for the transaction because we just allow shorting/negative amounts of stock or money 
                bid.quantity -= executed_quantity
                ask.quantity -= executed_quantity
                
                filled_orders.append((bid.uid, ask.uid, execution_price, executed_quantity, bid.oid, ask.oid))

                if bid.quantity == 0:
                    heapq.heappop(self.bids)
                if ask.quantity == 0:
                    heapq.heappop(self.asks)
            else:
                break
            
        return filled_orders
