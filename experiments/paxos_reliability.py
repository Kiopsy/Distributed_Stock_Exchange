import sys, time, statistics, subprocess, grpc, os, signal, threading
sys.path.append('../cs262-final-project')
import exchange_pb2
from helpers import nFaultStub
import constants as c

# Create a flag for signaling the threads to terminate
stop_threads = threading.Event()

def run_client_in_thread():
    stub = nFaultStub()
    if stub.connect():
        stub.backup_stub_connect_thread.start()
    
def run_institution_paxos_test(num_iterations, exchanges_count, exchanges_on_different_computers, run_time_seconds):

    exchanges = []
    for i in range(exchanges_count):
        if exchanges_on_different_computers:
            # Start exchange on a different computer using SSH
            exchange = subprocess.Popen(["ssh", "user@remote_host", "python3", "exchange.py", str(i)])
        else:
            # Start exchange on the same computer
            exchange = subprocess.Popen(["python3", f"exchange.py", str(i)])
        exchanges.append(exchange)

    threads = []
    for i in range(num_iterations):
        thread = threading.Thread(target=run_client_in_thread)
        threads.append(thread)
        thread.start()

    # Run threads for a given amount of seconds
    timer = threading.Timer(run_time_seconds, stop_threads.set)
    timer.start()

    for thread in threads:
        thread.join()

def run_institution_paxos_test():
    pass

# Example usage
run_institution_paxos_test(num_iterations=10)