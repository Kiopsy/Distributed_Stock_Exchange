# cs262-final-project
Distributed Stock Exchange


## Installation
- Clone the repository:
```bash
git clone https://github.com/alzh9000/cs262-final-project.git
```
- Ensure that the most recent version of Python is downloaded [here](https://www.python.org/downloads/)
- Ensure that correct dependencies are installed by running the following command:
```bash
pip install -r requirements.txt
```


## Setting up Servers and Clients

In constants.py, make sure to set the IP/HOST of each respective server before starting. Futhermore, ensure that the `NUM_SERVERS` constant matches the number of servers you want the exchange to use.

For example, servers with IDs = 0, 1, 2 have the respective IP's:
```bash
host = "10.250.78.119"
SERVER_IPS = {50050: host, 50051: host, 50052: host}
NUM_SERVERS = 3
```

To run the servers, splitting the server between different machines/terminals, you can run (where id = 0, 1, or 2).
```bash
python exchange.py id
```
Or to run all `NUM_SERVERS` servers in the same terminal using multiprocessing, you can run:
```bash
python exchange.py
```

Then, run the corresponding broker:
```bash
python broker.py
```

Lastly, start the websever that hosts the frontend client application used to interact with the service by running:
```bash
python UI/client_application.py
```

Navigate to the provided webpage, where you can perfom the client interactions. (Note: once the webserver is running, clients from any device can connect.)

## Tests
Tests are located in the `tests/` folder and should run automatically using the `python` command, such as by running `python tests/exchange_tests.py`. **You will need to have the correct host and number of servers set in the constants.py file in order to run the tests correctly**. Further tests can be run using the files in the `experiments/` directory, such as testing the latency of the exchange or using trading bots to test throughput and correctness.
