import time, statistics, subprocess, grpc, exchange_pb2
from client import BrokerClient

def run_latency_test(num_iterations, exchanges_count, clients_count, exchanges_on_different_computers=False):
    # Start timer
    start_time = time.time()
    
    # Start up exchanges
    exchanges = []
    for i in range(exchanges_count):
        if exchanges_on_different_computers:
            # Start exchange on a different computer using SSH
            exchange = subprocess.Popen(["ssh", "user@remote_host", "python3", "exchanges.py"])
        else:
            # Start exchange on the same computer
            exchange = subprocess.Popen(["python3", "exchanges.py"])
        exchanges.append(exchange)
    

    clients: list[BrokerClient] = []
    for i in range(clients_count):
        channel = grpc.insecure_channel(c.BROKER_IP[1] + ':' + str(c.BROKER_IP[0]))
        c = BrokerClient(channel)
        uid = i + 262
        c.Register(uid)
        clients.append(c)

    
    # Send deposit $1000 order and wait for confirmation
    for i in range(num_iterations):
        # TODO: implement sending deposit $1000 order and waiting for confirmation
        c = clients[0]
        c.DepositCash(1000)
        c.SendOrder(exchange_pb2.OrderType.BID, "GOOGL", 1, 100, 262)
        
        # Wait for client to get confirmation and stop timer
        stop_time = time.time()
        
        # Calculate latency
        latency = stop_time - start_time
        
        # Print latency for this iteration
        print(f"Iteration {i+1} latency: {latency} seconds")
        
        # Reset timer
        start_time = stop_time
        
    # Stop exchanges
    for exchange in exchanges:
        exchange.kill()
    
    # Calculate and print descriptive statistics
    latencies = [latency for _ in range(num_iterations)]
    mean = statistics.mean(latencies)
    std_dev = statistics.stdev(latencies)
    print(f"Mean latency: {mean} seconds")
    print(f"Standard deviation of latency: {std_dev} seconds")

# Example usage
run_latency_test(num_iterations=10, exchanges_count=3, clients_count=1)

# Example usage with variations
run_latency_test(num_iterations=10, exchanges_count=5, clients_count=1)
run_latency_test(num_iterations=10, exchanges_count=3, clients_count=1, exchanges_on_different_computers=True)
run_latency_test(num_iterations=10, exchanges_count=3, clients_count=5)
run_latency_test(num_iterations=10, exchanges_count=3, clients_count=1, exchanges_on_different_computers=True)
run_latency_test(num_iterations=10, exchanges_count=1, clients_count=5)
run_latency_test(num_iterations=10, exchanges_count=5, clients_count=5, exchanges_on_different_computers=True)
