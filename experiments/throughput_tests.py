import sys
sys.path.append('../cs262-final-project')
import trading_bots, initiate_servers


if __name__ == "__main__":
    initiate_servers.setup(3)
    trading_bots.setup(use_broker_client=True, run_test=True)
    trading_bots.setup(use_broker_client=False, run_test=True)
