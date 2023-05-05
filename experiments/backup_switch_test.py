import time, statistics, subprocess, grpc, exchange_pb2, os, signal
from helpers import nFaultStub
import constants as c

def measure_client_reconnect_time(exchanges_count, exchanges_on_different_computers = False):

    # Start up exchanges
    exchanges = []
    for i in range(exchanges_count):
        if exchanges_on_different_computers:
            # Start exchange on a different computer using SSH
            exchange = subprocess.Popen(["ssh", "user@remote_host", "python3", f"exchanges.py {i}"])
        else:
            # Start exchange on the same computer
            exchange = subprocess.Popen(["python3", f"exchanges.py {i}"])
        exchanges.append(exchange)
    
    stub = nFaultStub()
    if stub.connect():
            stub.backup_stub_connect_thread.start()
    
    index = stub.stub_dict["port"] - 50050
    os.killpg(os.getpgid(exchanges[index].pid), signal.SIGTERM)

    start_time = time.time()
    stub.Register(262+i)
    latency = time.time() - start_time