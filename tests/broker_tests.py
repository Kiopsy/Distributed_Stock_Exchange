import sys
sys.path.append('../cs262-final-project')
import broker, exchange, client, time, refresh
import constants as c
import exchange_pb2

def run_register_test(broker_client: client.BrokerClient,
                      broker_server: broker.Broker) -> None:
    result = broker_client.Register(1)
    assert result == True, "Failure while registering"
    result = broker_client.Register(2)
    assert result == True, "Failure while registering"
    result = broker_client.Register(-1)
    assert result == False, "Register succeeded when it should have failed"

def run_deposit_test(broker_client: client.BrokerClient, 
                     broker_server: broker.Broker) -> None:
    result = broker_client.DepositCash(1, 100000)
    assert result == True, "Failure depositing 100,000 dollars for uid 1"
    result = broker_client.DepositCash(2, 200000)
    assert result == True, "Failure depositing 200,000 dollars for uid 2"

def run_send_order_test(broker_client: client.BrokerClient, 
                        broker_server: broker.Broker) -> None:
    # Each stock starts with an IPO of 100 shares at $100 as per the spec
    msg, success = broker_client.SendOrder(exchange_pb2.OrderType.BID, "GOOGL", 100, 100, 1)

    assert success, msg

    time.sleep(1) # ensure with near-perfect probability that the broker receives the fill 

    # User 2 tries to ask to sell 100 shares at $100, but this should fail since they have no shares
    msg, success = broker_client.SendOrder(exchange_pb2.OrderType.ASK, "GOOGL", 100, 100, 2)
    assert not success, msg

    # User 2 asks to buy 50 @ 200   
    msg, success = broker_client.SendOrder(exchange_pb2.OrderType.BID, "GOOGL", 50, 200, 2)
    assert success, msg
    
    # User 1 will sell all 100 @ 200
    msg, success = broker_client.SendOrder(exchange_pb2.OrderType.ASK, "GOOGL", 50, 200, 1)
    assert success, msg

    time.sleep(1) # ensure with near-perfect probability that the broker receives the fill 

    # At this point, an order should be filled.
    # NOTE: MANUALLY VERIFY THAT THERE ARE TWO FILLS SHOWN ON SCREEN

tests = [run_register_test, run_deposit_test, run_send_order_test]

def main() -> None:
    refresh.depersist() # clear the pickle files
    exchange.setup(c.NUM_SERVERS, silent=False)
    time.sleep(5) # wait for exchange to start
    broker_server, _ = broker.setup()
    broker_client = client.setup()
    for test in tests:
        test(broker_client, broker_server)
        print(f"Passed {test.__name__}")

    print("Please check that two sets of fills have been printed on screen.")

if __name__ == "__main__":
    main()
