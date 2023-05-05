import time, statistics, grpc, multiprocessing, signal, sys
sys.path.append('../cs262-final-project')
import exchange_pb2
from client import BrokerClient
from broker import Broker
from exchange import ExchangeServer
from exchange_pb2_grpc import ExchangeServiceServicer, ExchangeServiceStub, add_ExchangeServiceServicer_to_server
from concurrent import futures
from helpers import sigint_handler
import constants as c

# exhanges = [ExchangeServer(i) for i in range(c.NUM_SERVERS)]

def run_broker_paxos_test(num_iterations):

    def serve(id):
        exchange = ExchangeServer(id)
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        add_ExchangeServiceServicer_to_server(exchange, server)
        server.add_insecure_port(exchange.HOST + ':' + str(exchange.PORT))
        server.start()
        exchange.sprint(f"Server initialized at {exchange.HOST} on port {exchange.PORT}")
        time.sleep(3)
        exchange.connect()
        exchange.heartbeat_thread.start()
        server.wait_for_termination()
    
    print("here")
    processes = []
    for i in range(c.NUM_SERVERS):
        process = multiprocessing.Process(target=serve, args=(i, ))
        processes.append(process)

    # Allow for ctrl-c exiting
    signal.signal(signal.SIGINT, sigint_handler)

    # Starts each process
    for process in processes:
        process.start()



    # Calculate and print descriptive statistics
    latencies = [latency for _ in range(num_iterations)]
    mean = statistics.mean(latencies)
    std_dev = statistics.stdev(latencies)
    print(f"Mean latency: {mean} seconds")
    print(f"Standard deviation of latency: {std_dev} seconds")

def run_institution_paxos_test():
    pass

# Example usage
run_broker_paxos_test(num_iterations=10)