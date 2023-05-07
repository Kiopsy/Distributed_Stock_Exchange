import unittest, threading, os, time, exchange_pb2, grpc, pickle
from limit_order_book import LimitOrderBook
from database import User
from exchange import ExchangeServer, setup
import constants as c
from helpers import nFaultStub
from refresh import depersist
from concurrent import futures
from exchange_pb2_grpc import ExchangeServiceServicer, ExchangeServiceStub, add_ExchangeServiceServicer_to_server

oid_counter = 0

class unit_tests(unittest.TestCase):

    def setUp(self):
        self.server1 = ExchangeServer(0, silent=True)
        self.server2 = ExchangeServer(1, silent=True)
        self.server3 = ExchangeServer(2, silent=True)

        # Simulate the connections between servers
        self.server1.peer_alive = {self.server2.PORT: True, self.server3.PORT: True}
        self.server2.peer_alive = {self.server1.PORT: True, self.server3.PORT: True}
        self.server3.peer_alive = {self.server1.PORT: True, self.server2.PORT: True}

    def test_exchange_initialization(self):
        # Check that the server was initialized correctly
        self.assertEqual(self.server1.ID, 0)
        self.assertEqual(self.server1.PORT, 50050)
        self.assertEqual(self.server1.HOST, c.host)
        peer_ports = {k: c.SERVER_IPS[k] for k in list(c.SERVER_IPS)[:c.NUM_SERVERS]}
        del peer_ports[50050]
        self.assertEqual(self.server1.PEER_PORTS, peer_ports)
        self.assertEqual(self.server1.peer_stubs, {})
        self.assertEqual(self.server1.primary_port, -1)
        self.assertEqual(self.server1.connected, False)
        self.assertEqual(self.server1.seen_ballots.max(), 0)

        # Check that the log file was created
        self.assertTrue(os.path.exists("./logs/server0.log"))

        # Check that the pickle file was created
        self.server1.db.store_data()
        self.assertTrue(os.path.exists("./pickles/server0.pkl"))

        # Check that the database was loaded or created correctly
        self.assertIsNotNone(self.server1.db)

    def test_leader_election_all_alive(self):
        # Test when all servers are alive
        primary_port = self.server1.leader_election()
        self.assertEqual(primary_port, self.server1.PORT)

        primary_port = self.server2.leader_election()
        self.assertEqual(primary_port, self.server1.PORT)

        primary_port = self.server3.leader_election()
        self.assertEqual(primary_port, self.server1.PORT)

        print("test_leader_election_all_alive passed.")

    def test_leader_election_one_dead(self):
        # Test when server1 is dead
        self.server1.peer_alive[self.server2.PORT] = False
        self.server1.peer_alive[self.server3.PORT] = False
        self.server2.peer_alive[self.server1.PORT] = False
        self.server3.peer_alive[self.server1.PORT] = False

        primary_port = self.server2.leader_election()
        self.assertEqual(primary_port, self.server2.PORT)

        primary_port = self.server3.leader_election()
        self.assertEqual(primary_port, self.server2.PORT)

        print("test_leader_election_one_dead passed.")

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

        print("test_add_order passed.")

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

        print("test_cancel_order passed.")

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

        print("test_match_orders passed.")
        
    def test_price_time_priority(self):
        # Test order matching and execution with different scenarios
        book = LimitOrderBook(unit_testing=True)
        user1 = User("user1", 1000)
        user2 = User("user2", 1000)
        user3 = User("user3", 1000)

        # Scenario 1: Check that user1's order is executed first because it has the highest price
        book.add_order("bid", 10, 5, user1, oid_counter)
        book.add_order("bid", 10, 5, user3, oid_counter)
        filled_orders = book.add_order("ask", 10, 5, user2, oid_counter)

        assert len(book.bids) == 1, "Failed to clear bid order book after execution"
        assert len(book.asks) == 0, "Failed to clear ask order book after execution"
        assert filled_orders[0][0] == user1, "Incorrect bid order user after execution"
        assert filled_orders[0][1] == user2, "Incorrect ask order user after execution"
        assert filled_orders[0][2] == 10, "Incorrect executed price"
        assert filled_orders[0][3] == 5, "Incorrect executed size"
        
        print("test_price_time_priority passed.")

    def test_price_time_priority_latency(self):
        # Test order matching and execution with different scenarios
        book = LimitOrderBook(unit_testing=True)
        user1 = User("user1", 1000)
        user2 = User("user2", 1000)
        user3 = User("user3", 1000)

        # Scenario 1: Check that user1's order is executed first because it has the oldest timestamp even though user3 tried to send their order earlier
        print(f"I am user3 and I am trying to send my order right now but I have high latency.")
        book.add_order("bid", 10, 5, user1, oid_counter)
        book.add_order("bid", 10, 5, user3, oid_counter)
        filled_orders = book.add_order("ask", 10, 5, user2, oid_counter)

        assert len(book.bids) == 1, "Failed to correctly clear bid order book after execution"
        assert len(book.asks) == 0, "Failed to clear ask order book after execution"
        assert filled_orders[0][0] == user1, "Incorrect bid order user after execution"
        assert filled_orders[0][1] == user2, "Incorrect ask order user after execution"
        assert filled_orders[0][2] == 10, "Incorrect executed price"
        assert filled_orders[0][3] == 5, "Incorrect executed size"

        print("test_price_time_priority_latency passed.")

    def tearDown(self):
        self.server1.log_file.close()
        self.server2.log_file.close()
        self.server3.log_file.close()

        del self.server1
        del self.server2
        del self.server3
        
import exchange_pb2_grpc
class integration_tests(unittest.TestCase):

    def setUp(self):
        depersist()
        self.processes = setup(3, True)
        time.sleep(5)


    def test_client_exchange_connection(self):
        channel = grpc.insecure_channel(f"{c.SERVER_IPS[50050]}:50050") 
        exch_stub = exchange_pb2_grpc.ExchangeServiceStub(channel)
        res = exch_stub.Ping(exchange_pb2.Empty())

        # Exchange can be reached
        self.assertEqual(res, exchange_pb2.Empty())
        print("test_client_exchange_connection passed.")

    @staticmethod
    def concurrent_exchange_requests(ids = [0, 1, 2], max_secs = 15):

        stubs = {i: exchange_pb2_grpc.ExchangeServiceStub(grpc.insecure_channel(f"{c.SERVER_IPS[50050 + i]}:{50050+i}")) for i in ids}
        

        def desposit_for_broker(key_index):
            for _ in range(max_secs):
                import random
                time.sleep(random.uniform(0, 1))
                stubs[key_index].DepositCash(exchange_pb2.Deposit(uid=c.BROKER_KEYS[key_index], amount=random.randint(1,40)))

        threads = []
        for i in ids:
            thread = threading.Thread(target=desposit_for_broker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for t in threads:
            t.join()
        
    def test_paxos_agreement(self):
        depersist()
        
        integration_tests.concurrent_exchange_requests()

        with open('./pickles/server0.pkl', 'rb') as f:
            data1 = pickle.load(f)

        with open('./pickles/server1.pkl', 'rb') as f:
            data2 = pickle.load(f)

        with open('./pickles/server2.pkl', 'rb') as f:
            data3 = pickle.load(f)

        # Compare the data in pickle files
        self.assertEqual(data1, data2, "Data in server0.pkl and server1.pkl is not consistent")
        self.assertEqual(data3, data1, "Data in server2.pkl and server0.pkl is not consistent")
        self.assertEqual(data3, data2, "Data in server2.pkl and server1.pkl is not consistent")

        print("test_paxos_agreement passed.")
    
    def test_paxos_agreement_after_failure(self):
        depersist()

        integration_tests.concurrent_exchange_requests(max_secs=5)

        # kill exchange 0
        self.processes[0].terminate()

        integration_tests.concurrent_exchange_requests(ids = [1, 2], max_secs=5)

        with open('./pickles/server0.pkl', 'rb') as f:
            data1 = pickle.load(f)

        with open('./pickles/server1.pkl', 'rb') as f:
            data2 = pickle.load(f)

        with open('./pickles/server2.pkl', 'rb') as f:
            data3 = pickle.load(f)

        # Compare the data in pickle files
        self.assertNotEqual(data1, data2, "Data in server0.pkl and server1.pkl is not consistent")
        self.assertNotEqual(data3, data1, "Data in server2.pkl and server0.pkl is not consistent")
        self.assertEqual(data3, data2, "Data in server2.pkl and server1.pkl is not consistent")

        print("test_paxos_agreement_after_failure passed.")



        
        
if __name__ == '__main__':
    unittest.main()
