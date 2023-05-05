import multiprocessing, random, grpc, exchange_pb2, threading, time, signal
from client import BrokerClient
from institution import InstitutionClient
import constants as c
from helpers import sigint_handler
from typing import Optional

class NaiveBot():
    def __init__(self, uid: int, use_broker_client: bool) -> None:
        self.uid = uid
        self.client = BrokerClient() if use_broker_client else InstitutionClient(uid)

        # Register
        if use_broker_client:
            self.client.Register(uid)

        # Deposit sufficient funds
        init_cash = random.randint(500, 100_000)
        self.client.DepositCash(uid, init_cash)
    
    def run_throughput_test(self) -> None:
        ticker = c.TICKERS[0]
        price = 100
        self.client.DepositCash(self.uid, 1000000)
        start_time = time.time()
        while True:
            if time.time() - start_time >= 5:
                break
            num_runs += 1

        print(f"Made {num_runs} orders in 5 seconds")

    def run(self) -> None:
        while True:
            self.make_order()

    def make_order(self):
        BID_ASK = [exchange_pb2.OrderType.BID, exchange_pb2.OrderType.ASK]
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
    

def setup(use_broker_client: Optional[bool] = None, run_test: Optional[bool] = None):
    if not use_broker_client:
        inp = input("Use broker client? [Y/n]")
        use_broker_client = not (inp == 'n' or inp == 'N')
    if not run_test:
        inp = input("Run throughput test? [Y/n]")
        run_test = not (inp == 'n' or inp == 'N')
    processes = []
    bots = []

    for i in range(c.NUM_BOTS):
        uid = c.BROKER_KEYS[i + 1] if not use_broker_client else len(processes) + 262
        bots.append(NaiveBot(uid, use_broker_client))
        process = multiprocessing.Process(target=bots[i].run, args=(uid, use_broker_client))
        processes.append(process)

    # Allow for ctrl-c exiting
    signal.signal(signal.SIGINT, sigint_handler)

    # Starts each process
    for process in processes:
        process.start()

if __name__ == "__main__":
    print(f"Running {c.NUM_BOTS} bots...")
    setup()
