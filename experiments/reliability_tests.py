import time, statistics, subprocess, grpc, exchange_pb2
from client import BrokerClient

def run_latency_test(num_iterations, exchanges_count, clients_count, exchanges_on_different_computers=False):
    

    # Calculate and print descriptive statistics
    latencies = [latency for _ in range(num_iterations)]
    mean = statistics.mean(latencies)
    std_dev = statistics.stdev(latencies)
    print(f"Mean latency: {mean} seconds")
    print(f"Standard deviation of latency: {std_dev} seconds")

# Example usage
run_latency_test(num_iterations=10, exchanges_count=3, clients_count=1)