import sys
sys.path.append('../cs262-final-project')
import time, statistics, subprocess, grpc, exchange_pb2, initiate_servers, institution
import constants
from client import BrokerClient

def run_latency_test(num_iterations, exchanges_count, clients_count):
    servers = initiate_servers.setup(exchanges_count)

    clients: list[institution.InstitutionClient] = []
    uids: list[int] = []
    for i in range(clients_count):
        client = institution.InstitutionClient(constants.BROKER_KEYS[i + 1])
        uid = constants.BROKER_KEYS[i + 1]
        clients.append(client)
        uids.append(uid)

    
    latencies: list[float] = []
    # Send deposit $1000 order and wait for confirmation
    for i in range(num_iterations):
        # Start timer
        start_time = time.time()
    
        c = clients[0]
        uid = uids[0]
        c.DepositCash(uid, 1000)
        c.SendOrder(exchange_pb2.OrderType.BID, "GOOGL", 1, 100, uid)
        
        # Wait for client to get confirmation and stop timer
        stop_time = time.time()
        
        # Calculate latency
        latency = stop_time - start_time

        latencies.append(latency)
        
        # Print latency for this iteration
        print(f"Iteration {i+1} latency: {latency} seconds")
        
        # Reset timer
        start_time = stop_time
    
    # Calculate and print descriptive statistics
    mean = statistics.mean(latencies)
    std_dev = statistics.stdev(latencies)
    print(f"Mean latency: {mean} seconds")
    print(f"Standard deviation of latency: {std_dev} seconds")
    initiate_servers.tear_down(servers)

if __name__ == "__main__":
    print("How many exchanges?")
    exchg_count = int(input("> "))
    print("How many iterations?")
    iterations = int(input("> "))
    print("How many clients?")
    client_count = int(input("> "))
    constants.NUM_SERVERS = exchg_count
    run_latency_test(num_iterations=iterations, 
                     exchanges_count=exchg_count, 
                     clients_count=client_count)
