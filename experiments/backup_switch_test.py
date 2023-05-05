import sys
sys.path.append('../cs262-final-project')
import time, statistics, subprocess, grpc, exchange_pb2, os, signal
from helpers import nFaultStub
import constants as c
from refresh import depersist

def measure_client_reconnect_time(exchanges_count, exchanges_on_different_computers = False):
    depersist()
    # Start up exchanges
    exchanges: list[subprocess.Popen] = []
    for i in range(exchanges_count):
        if exchanges_on_different_computers:
            # Start exchange on a different computer using SSH
            exchange = subprocess.Popen(["ssh", "user@remote_host", "python3", "exchange.py", str(i)])
        else:
            # Start exchange on the same computer
            exchange = subprocess.Popen(["python3", "exchange.py", str(i)])
        exchanges.append(exchange)

    for i in range(10, 0, -1):
        print(f"Testing in {i}")
        time.sleep(1)
    
    stub = nFaultStub()
    if stub.connect():
            stub.backup_stub_connect_thread.start()

    start_time = time.time()
    stub.DepositCash(exchange_pb2.Deposit(uid=c.BROKER_KEYS[0], amount=10))
    latency1 = time.time() - start_time
    print(f"Connection time: {latency1}")
    
    index = stub.stub_dict["port"] - 50050
    exchanges[index].terminate()

    print(f"Killing exchange with id {index}")

    for i in range(4, 0, -1):
        print(f"Testing in {i}")
        time.sleep(1)

    start_time = time.time()
    stub.DepositCash(exchange_pb2.Deposit(uid=c.BROKER_KEYS[0], amount=10))
    latency2 = time.time() - start_time
    print(f"Reconnection time: {latency2}")

    for exch in exchanges:
        try:
            exch.terminate()
        except Exception as e:
            print(f"Error: {e}")

    print(latency1, latency2)

    
if __name__ == "__main__":
    measure_client_reconnect_time(3)