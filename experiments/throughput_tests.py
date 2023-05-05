import sys
sys.path.append('../cs262-final-project')
import trading_bots, initiate_servers


if __name__ == "__main__":
    print("How many exchanges should be run?")
    num_servers = int(input("> "))
    print("Press enter once this test has concluded.")

    server_tuple = initiate_servers.setup(num_servers)
    trading_bots.setup(use_broker_client=False, run_test=True)
    input("")
    initiate_servers.tear_down(server_tuple)

    # print("Press enter once this test has concluded.")
    # server_tuple = initiate_servers.setup(num_servers)
    # trading_bots.setup(use_broker_client=True, run_test=True)
    # input("")
    # initiate_servers.tear_down(server_tuple)
