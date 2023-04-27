import unittest
from limit_order_book import User, LimitOrderBook


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

    def test_broker_consensus():
        # TODO
        pass

    # TESTING LIMIT ORDER BOOK

    def test_add_order(self):
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

    def test_cancel_order(self):
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

    def test_match_orders(self):
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

if __name__ == '__main__':
    print("Begining unit tests...")
    unittest.main()