import sys, time
sys.path.append('../cs262-final-project')
import broker, client, exchange
from typing import Tuple, Any

def setup(num_exchanges: int) -> broker.Broker:
    print("Initiating exchanges")
    exchange.setup(num_exchanges)
    print("Done initiating exchanges. Waiting for exchanges to connect.")
    time.sleep(5)
    print("Initiating broker")
    exchg_client, _ = broker.setup()
    print("Done initiating broker")
    return exchg_client

def tear_down() -> None:
    pass

if __name__ == "__main__":
    print("How many exchanges should be initiated?")
    num_exchanges = int(input("> "))
    setup(num_exchanges)
