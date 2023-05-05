import sys
sys.path.append('../cs262-final-project')
import trading_bots

trading_bots.setup(use_broker_client=True, run_test=True)
trading_bots.setup(use_broker_client=False, run_test=True)