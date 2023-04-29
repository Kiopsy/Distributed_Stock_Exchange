from collections import defaultdict
import pickle
from limit_order_book import LimitOrderBook, User
import constants as c

# simply use this class like it is a dictionary, it will store data automatically
class Database():
    def __init__(self, filename = './db.pkl') -> None:
        self.db = None
        self.filename = filename
        self.load_data()

    def turn_bytes_into_db(self, b: bytes):
        self.db = pickle.loads(b)
        
    def store_data(self):
        """
        It opens db.pkl file in write binary mode, and then dumps our db to the file.
        """
        with open(self.filename, 'wb') as dbfile:
            pickle.dump(self.db, dbfile)

    def load_data(self):
        """
        Load the dictionary from the db.pkl file if it exists, otherwise create it.

        Return a dictionary with two keys, "passwords" and "messages".
        """
        try:
            with open(self.filename, 'rb')  as dbfile:
                self.db = pickle.load(dbfile)
        except:
            self.db = {
                "orderbooks" : defaultdict(LimitOrderBook),
                "client_balance": {client: 0 for client in c.USER_KEYS},
                "oid_count": 0,
                "oid_to_ticker": {},
                "uid_to_user_dict": {uid: User(uid, balance=0) for uid in c.USER_KEYS},
            }
        return self.db
    
    def get_db(self):
        return self.db
   