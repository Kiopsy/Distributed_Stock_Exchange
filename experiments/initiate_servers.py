import sys
sys.path.append('../cs262-final-project')
import broker, client, exchange
from typing import Tuple, Any

def setup(num_exchanges: int) -> broker.Broker:
    exchange.setup(num_exchanges)
    exchg_client, _ = broker.setup()
    return exchg_client

def tear_down() -> None:
    pass

if __name__ == "__main__":
    print("How many exchanges should be initiated?")
    num_exchanges = int(input("> "))
    setup(num_exchanges)
