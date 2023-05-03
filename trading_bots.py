import multiprocessing, random, grpc, exchange_pb2, threading, time, signal
from client import BrokerClient
import constants as c
from helpers import sigint_handler

def stupid_bot(uid: int):
    channel = grpc.insecure_channel(f"{c.BROKER_IP[1]}:{c.BROKER_IP[0]}")
    broker_client = BrokerClient(channel)

    BID_ASK = [exchange_pb2.OrderType.BID, exchange_pb2.OrderType.ASK]

    # Register
    broker_client.Register(uid)

    # Deposit sufficient funds
    init_cash = random.randint(500, 100_000)
    broker_client.DepositCash(uid, init_cash)

    # Make Bids or Asks
    while True:
        
        variance = random.uniform(-1, 1)
        time.sleep(c.BOT_ORDER_RATE + variance)
        
        bid_ask = random.choice([0, 1])

        ticker = random.choice(c.TICKERS)

        shares = random.randint(1, 50)

        price = random.randint(10, 100) if bid_ask == 0 else random.randint(100, 200)

        msg, success = broker_client.SendOrder(BID_ASK[bid_ask], ticker, shares, price, uid)

        if success:
            print(f"Bot {uid}: Placed a {'bid' if bid_ask == 0 else 'ask'} for {shares} stocks of {ticker} at {price} per share")
        else:
            print(f"Bot {uid}: Error on order: {msg}")


def main():
    processes = []

    for i in range(c.NUM_BOTS):
        process = multiprocessing.Process(target=stupid_bot, args=(i+262, ))
        processes.append(process)

    # Allow for ctrl-c exiting
    signal.signal(signal.SIGINT, sigint_handler)

    # Starts each process
    for process in processes:
        process.start()

if __name__ == "__main__":
    print(f"Running {c.NUM_BOTS} bots...")
    main()
