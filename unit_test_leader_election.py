import unittest
from exchange import ExchangeServer
import constants as c

class TestExchangeServer(unittest.TestCase):

    def setUp(self):
        self.server1 = ExchangeServer(1, silent=True)
        self.server2 = ExchangeServer(2, silent=True)
        self.server3 = ExchangeServer(3, silent=True)

        # Simulate the connections between servers
        self.server1.peer_alive = {self.server2.PORT: True, self.server3.PORT: True}
        self.server2.peer_alive = {self.server1.PORT: True, self.server3.PORT: True}
        self.server3.peer_alive = {self.server1.PORT: True, self.server2.PORT: True}

    def test_leader_election_all_alive(self):
        # Test when all servers are alive
        primary_port = self.server1.leader_election()
        self.assertEqual(primary_port, self.server1.PORT)

        primary_port = self.server2.leader_election()
        self.assertEqual(primary_port, self.server1.PORT)

        primary_port = self.server3.leader_election()
        self.assertEqual(primary_port, self.server1.PORT)

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

    def tearDown(self):
        del self.server1
        del self.server2
        del self.server3

if __name__ == "__main__":
    unittest.main()
