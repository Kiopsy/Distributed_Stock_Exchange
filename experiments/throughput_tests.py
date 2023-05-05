import sys
sys.path.append('../cs262-final-project')
import trading_bots, initiate_servers


if __name__ == "__main__":
    print("How many exchanges should be run?")
    num_servers = int(input("> "))
    initiate_servers.setup(num_servers)
    trading_bots.setup(use_broker_client=False, run_test=True)
    print("Running next test...")
    trading_bots.setup(use_broker_client=True, run_test=True)
