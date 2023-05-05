import unittest
from limit_order_book import LimitOrderBook
from database import User

oid_counter = 0


class unit_tests(unittest.TestCase):

    # TESTING EXCHANGE CONSENSUS

    def test_exchange_connection(self):
        # TODO
        pass

    def test_paxos_consensus(self):
        # TODO
        pass

    def test_leader_election(self):
        # TODO
        pass

    # TESTING BROKER

    def test_broker_consensus(self):
        # TODO
        pass

    # TESTING LIMIT ORDER BOOK

    def test_add_order(self):
        # Test adding bid and ask orders and check if they are stored correctly in the order book
        book = LimitOrderBook(unit_testing=True)
        user1 = User("user1", "password1")
        user2 = User("user2", "password2")

        book.add_order("bid", 10, 5, user1, oid_counter)
        assert len(book.bids) == 1, "Failed to add bid order to order book"

        book.add_order("ask", 12, 3, user2 , oid_counter)
        assert len(book.asks) == 1, "Failed to add ask order to order book"

        book.add_order("bid", 9, 7, user1, oid_counter)
        assert len(book.bids) == 2, "Failed to add multiple bid orders to order book"

        book.add_order("ask", 15, 2, user2, oid_counter)
        assert len(book.asks) == 2, "Failed to add multiple ask orders to order book"

        assert book.bids[0][2].price == 10, "Incorrect bid order price"
        assert book.bids[0][2].quantity == 5, "Incorrect bid order quantity"
        assert book.bids[0][2].uid == user1, "Incorrect bid order user"

        assert book.asks[0][2].price == 12, "Incorrect ask order price"
        assert book.asks[0][2].quantity == 3, "Incorrect ask order quantity"
        assert book.asks[0][2].uid == user2, "Incorrect ask order user"

    def test_cancel_order(self):
        # Test canceling bid and ask orders and check if they are removed from the order book
        book = LimitOrderBook(unit_testing=True)
        user1 = User("user1", "password1")
        user2 = User("user2", "password2")

        book.add_order("bid", 10, 5, user1, oid_counter)
        book.add_order("ask", 12, 3, user2, oid_counter)

        assert book.cancel_order_by_price("bid", 10, user1) == True, "Failed to cancel bid order"
        assert len(book.bids) == 0, "Bid order not removed from order book"

        assert book.cancel_order_by_price("ask", 12, user2) == True, "Failed to cancel ask order"
        assert len(book.asks) == 0, "Ask order not removed from order book"

        assert book.cancel_order_by_price("bid", 10, user1) == False, "Incorrectly canceled non-existing bid order"
        assert book.cancel_order_by_price("ask", 12, user2) == False, "Incorrectly canceled non-existing ask order"

    def test_match_orders(self):
        # Test order matching and execution with different scenarios
        book = LimitOrderBook(unit_testing=True)
        user1 = User("user1", 1000)
        user2 = User("user2", 1000)

        # Scenario 1: Exact match between bid and ask
        book.add_order("bid", 10, 5, user1, oid_counter)
        filled_orders = book.add_order("ask", 10, 5, user2, oid_counter)

        assert len(book.bids) == 0, "Failed to clear bid order book after execution"
        assert len(book.asks) == 0, "Failed to clear ask order book after execution"
        assert filled_orders[0][0] == user1, "Incorrect bid order user after execution"
        assert filled_orders[0][1] == user2, "Incorrect ask order user after execution"
        assert filled_orders[0][2] == 10, "Incorrect executed price"
        assert filled_orders[0][3] == 5, "Incorrect executed size"
        
    def test_price_time_priority(self):
        # Test order matching and execution with different scenarios
        book = LimitOrderBook(unit_testing=True)
        user1 = User("user1", 1000)
        user2 = User("user2", 1000)
        user3 = User("user3", 1000)

        # Scenario 1: Exact match between bid and ask
        book.add_order("bid", 10, 5, user1, oid_counter)
        book.add_order("bid", 10, 5, user3, oid_counter)
        filled_orders = book.add_order("ask", 10, 5, user2, oid_counter)

        assert len(book.bids) == 1, "Failed to clear bid order book after execution"
        assert len(book.asks) == 0, "Failed to clear ask order book after execution"
        assert filled_orders[0][0] == user1, "Incorrect bid order user after execution"
        assert filled_orders[0][1] == user2, "Incorrect ask order user after execution"
        assert filled_orders[0][2] == 10, "Incorrect executed price"
        assert filled_orders[0][3] == 5, "Incorrect executed size"

if __name__ == '__main__':
    print("Begining unit tests...")
    unittest.main()