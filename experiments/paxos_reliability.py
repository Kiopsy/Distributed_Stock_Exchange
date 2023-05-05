import sys
sys.path.append('../cs262-final-project')
# sys.path.append('C:/Users/vg210\Desktop/cs262-final-project/')
import time, threading, exchange_pb2, exchange, multiprocessing, subprocess
from helpers import nFaultStub
import constants as c
import csv
import statistics
from client import BrokerClient
import broker

# Create a flag for signaling the threads to terminate
stop_threads = threading.Event()

csv_file = "./testing/server0.csv"

def run_client_in_thread(thread_id):

    stub = nFaultStub()
    if stub.connect():
        stub.backup_stub_connect_thread.start()
        while not stop_threads.is_set():
            stub.DepositCash(exchange_pb2.Deposit(uid=c.BROKER_KEYS[0], amount=10))

    print(f"Thread {thread_id} completed.")

    
def run_broker_client_in_thread(thread_id):
    broker_client = BrokerClient()

    while not stop_threads.is_set():
        broker_client.stub.DepositCash(exchange_pb2.Deposit(uid=c.BROKER_KEYS[0], amount=10))

    print(f"Thread {thread_id} completed.")

def run_institution_paxos_test(num_iterations, client_count, exchanges_count, run_time_seconds):

    results = []  # Initialize an empty list to store results

    for seconds in run_time_seconds:
        failed_commits = []
        
        for j in range(num_iterations):
            exchanges: list[subprocess.Popen] = []

            for i in range(exchanges_count):
                
                # Start exchange on the same computer
                exchange = subprocess.Popen(["python", "exchange.py", str(i)])
                exchanges.append(exchange)

            time.sleep(c.CONNECTION_WAIT_TIME + 1)

            threads = []
            for i in range(client_count):
                thread = threading.Thread(target=run_client_in_thread, args=(i,))
                threads.append(thread)
                thread.start()

            # Run threads for a given amount of seconds
            print(f"Setting runtime: {seconds}")
            timer = threading.Timer(seconds, stop_threads.set)
            timer.start()

            for thread in threads:
                thread.join()

            while not stop_threads.is_set():
                pass

            # Read the CSV file and get the current value of failed_commit
            with open(csv_file, mode='r', newline='') as file:
                reader = csv.reader(file)
                next(reader)  # Skip the header row
                for row in reader:
                    failed_commit = int(row[0])
                    failed_commits.append(failed_commit)

            stop_threads.clear()

            # Terminate the exchange processes
            for exchange in exchanges:
                exchange.terminate()

            # Wait for the exchange processes to exit
            for exchange in exchanges:
                exchange.wait()

            print("All nFaultStub threads have completed.")

            print(f"Runtime {seconds}: iteration {j}, failed_commit: {failed_commit}")
        
        mean = statistics.mean(failed_commits)
        stdev = statistics.stdev(failed_commits) if len(failed_commits) > 1 else 0

        # Add results for this iteration to the results list
        res = {
            "runtime": seconds,
            "failed_commits": failed_commits,
            "mean": mean,
            "stdev": stdev,
        }
        results.append(res)
        print(f"Runtime {seconds}: result statistics: {res}")

    # Print all results at the end of the program
    for result in results:
        print(f"\nFor runtime {result['runtime']}s:")
        print(f"  Failed commits: {result['failed_commits']}")
        print(f"  Mean: {result['mean']:.2f}")
        print(f"  Standard deviation: {result['stdev']:.2f}")

run_institution_paxos_test(10, 5, 4, [5, 10, 15, 20])