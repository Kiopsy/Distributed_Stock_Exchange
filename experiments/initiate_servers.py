import sys, time
sys.path.append('../cs262-final-project')
import broker, exchange
import multiprocessing
import threading
from typing import Tuple, List, Any

def setup(num_exchanges: int) -> Tuple[Any, broker.Broker, List[multiprocessing.Process]]:
    print("Initiating exchanges")
    exchange_servers = exchange.setup(num_exchanges)
    print("Done initiating exchanges. Waiting for exchanges to connect.")
    time.sleep(5)
    print("Initiating broker")
    exchange_client, broker_server = broker.setup()
    print("Done initiating broker")
    return (broker_server, exchange_client, exchange_servers)

def tear_down(setup_tuple: Tuple[Any, broker.Broker, List[multiprocessing.Process]]) -> None:
    print("Tearing down servers and broker client")
    broker_server, exchange_client, exchange_servers = setup_tuple
    exchange_client.shutdown = True
    exchange_client.stub.disconnect()
    broker_server.stop(grace=None)
    for server in exchange_servers:
        server.kill()
    print("Done tearing down")

if __name__ == "__main__":
    print("How many exchanges should be initiated?")
    num_exchanges = int(input("> "))
    setup(num_exchanges)
