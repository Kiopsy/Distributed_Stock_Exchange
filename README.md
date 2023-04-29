pip install grpcio
and 
pip install grpcio-tools


# cs262-final-project
Distributed Stock Exchange


## Installation
- Clone the repository:
```bash
git clone https://github.com/alzh9000/cs262-final-project.git
```
- Ensure that the most recent version of Python is downloaded [here](https://www.python.org/downloads/)
- Ensure that gRPC is downloaded for Python using the following commands
```bash
pip install grpcio
pip install grpcio-tools
```
- We use Tkinter for the GUI, so download it with the following command:
```bash
pip install tk
```


# Tasks 
Think about project as building out each of the 3 design projects (DP)

High level tasks:
Come up with metrics to track for all our experiments.
READ THE GOOGLE DOC

DP 1:
- [ ] Handling networking, sockets, wire protocol, etc. for communicating between clients and servers, where there is just 1 central server that runs orderbook 
- [ ] Make separate files for client.py and server.py, server.py runs the orderbook, client runs the UI 
  - [ ] Probably need threads on the server to handle clients, and client needs 2 threads, 1 for network, 1 for UI
- [ ] Like in DP 1, there is no persistence, no replication, no logical clocks, YET. we implement these in later tasks 
- [ ] Move unit tests to a separate file 

RUN EXPERIMENTS ON DP1 LEVEL STOCK EXCHANGE. TRACK ALL THOSE METRICS. For dp1, we can say the only timestamps that matter are when the server receives the orders. So server is always correct - whenever server receives order is the timestamp for that order.

DP 2:
- [] Add logical clocks or vector clocks to DP1.
- [] See if, before doing DP 2, you get problems with ordering if clients try to send orders at same time. 

Do timestamping on client side. Do experiments. Does logical clocks (or vector clocks) make system more well-ordered/solve ordering problems? 

DP 3:
- [] Add persistence to DP2. Track things even if server goes offline. Store info about users' portfolios (rn just stock and money), store info about previous trades (who bought what, when, how much, etc.) in case u need to investigate something later (like how stock exchanges store everything about trades in case u need ot investigate insider trading, for example).
- [] add replication to DP2. Have the stock exchange still work even if the primary/current server goes down.

Do more experiments. 

Write the paper
When we present, we can demo the stock exchang app, and then talk about the experiments we did, and then talk about the paper/analysis of the results of the experiments.