# HOST/PORT INFO
host = "10.228.152.239"
SERVER_IPS = {50050: host, 50051: host, 50052: host, 50053: host, 50054: host}
BROKER_IP = (40050, host)

# EXCHANGE
HEARTRATE = 3
NUM_SERVERS = 3
CONNECTION_WAIT_TIME = 3
MAX_VOTE_ATTEMPTS = 5
LOG_DIR = "logs"
PKL_DIR = "pickles"
DIVIDER = "*(&*^&%^$%^)"

# BROKER 
BACKGROUND_STUB_REFRESH_RATE = 1
EXCHANGE_FEE = 1
BROKER_FEE = 1
BROKER_KEYS = [0, 1, 2]

# MISC.
TICKERS = ["GOOGL", "AAPL", "MSFT"]

# BOTS
BOT_ORDER_RATE = 5
NUM_BOTS = 5
BOT_ORDER_RATE_VARIANCE = 1

for i in range(NUM_BOTS):
    BROKER_KEYS.append(i + 1)
