import grpc, sys, signal, multiprocessing, time, socket
from helpers import Constants as c
from concurrent import futures
import exchange_pb2 as exchange_pb2
from exchange_pb2_grpc import ExchangeServiceServicer, ExchangeServiceStub, add_ExchangeServiceServicer_to_server
from exchange import ExchangeServer

# func "serve": starts an exchange server
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

# clean control c exiting
def sigint_handler(signum, frame):
    # terminate all child processes
    for process in multiprocessing.active_children():
        process.terminate()
    # exit the main process without raising SystemExit
    try:
        sys.exit(0)
    except SystemExit:
        pass

def main():
    # Allow for server creation by id through command-line args
    if len(sys.argv) == 2:
        try:
            machine_id = int(sys.argv[1])
            connection_wait_time = 5
            serve(machine_id)
        except KeyboardInterrupt:
            pass
    else:
        processes = []
    
        # Spawns a new process for each server that we have to run 
        for i in range(c.NUM_SERVERS):
            process = multiprocessing.Process(target=serve, args=(i, ))
            processes.append(process)

        # Allow for ctrl-c exiting
        signal.signal(signal.SIGINT, sigint_handler)

        # Starts each process
        for process in processes:
            process.start()

if __name__ == '__main__':
    # Get your own hostname:
    hostname = socket.gethostbyname(socket.gethostname())
    print("Hostname:", hostname)
    main()