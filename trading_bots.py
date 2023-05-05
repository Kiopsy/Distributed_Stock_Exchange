import multiprocessing, random, grpc, exchange_pb2, threading, time, signal
from client import BrokerClient
from institution import InstitutionClient
import constants as c
from helpers import sigint_handler
from typing import Optional, List

BID_ASK = [exchange_pb2.OrderType.BID, exchange_pb2.OrderType.ASK]

class NaiveBot():
    def __init__(self, uid: int, use_broker_client: bool) -> None:
        self.uid = uid
        self.use_broker_client = use_broker_client

    def initialize(self) -> None:
        # Needed since multiprocessing doesn't support pickling gRPC objects
        self.client = BrokerClient() if self.use_broker_client else InstitutionClient(self.uid)

        # Register
        if self.use_broker_client:
            self.client.Register(self.uid)

        # Deposit sufficient funds
        init_cash = random.randint(500, 100_000)
        self.client.DepositCash(self.uid, init_cash)
    
    def run_throughput_test(self) -> None:
        self.initialize()
        num_runs = 0
        self.client.DepositCash(self.uid, 1000000)
        ticker = c.TICKERS[0]
        price = 100
        start_time = time.time()
        while True:
            if time.time() - start_time >= 5:
                break
            order_type = BID_ASK[num_runs % 2]
            self.client.SendOrder(order_type, ticker, 1, price, self.uid)
            num_runs += 1

        print(f"Made {num_runs} orders in 5 seconds")

    def run(self) -> None:
        while True:
            self.make_random_order()

    def make_random_order(self):
        self.initialize()
        variance = random.uniform(-c.BOT_ORDER_RATE_VARIANCE, c.BOT_ORDER_RATE_VARIANCE)
        time.sleep(c.BOT_ORDER_RATE + variance)
        
        bid_ask = random.choice([0, 1])

        ticker = random.choice(c.TICKERS)

        shares = random.randint(1, 50)

        price = random.randint(10, 200) if bid_ask == 0 else random.randint(50, 200)
        
        msg, success = self.client.SendOrder(BID_ASK[bid_ask], ticker, shares, price, self.uid)

        if success:
            print(f"Bot {self.uid}: Placed a {'bid' if bid_ask == 0 else 'ask'} for {shares} stocks of {ticker} at {price} per share")
        else:
            print(f"Bot {self.uid}: Error on order: {msg}")
    

def setup(num_bots: int = c.NUM_BOTS, use_broker_client: Optional[bool] = None, run_test: Optional[bool] = None):
    if use_broker_client is None:
        inp = input("Use broker client? [Y/n]")
        use_broker_client = not (inp == 'n' or inp == 'N')
    if run_test is None:
        inp = input("Run throughput test? [Y/n]")
        run_test = not (inp == 'n' or inp == 'N')
    processes: List[multiprocessing.Process] = []
    bots = []

    for i in range(num_bots):
        print(f"Setting up bot {i}")
        uid = c.BROKER_KEYS[i + 1] if not use_broker_client else len(processes) + 262
        bot = NaiveBot(uid, use_broker_client)
        bots.append(bot)
        target = bot.run_throughput_test if run_test else bot.run
        process = multiprocessing.Process(target=target, args=())
        processes.append(process)

    # Allow for ctrl-c exiting
    signal.signal(signal.SIGINT, sigint_handler)

    # Starts each process
    for process in processes:
        process.start()

    print("Done setting up")

if __name__ == "__main__":
    print(f"Running {c.NUM_BOTS} bots...")
    setup()
