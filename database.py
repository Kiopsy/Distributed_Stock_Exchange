from collections import defaultdict
import pickle
from limit_order_book import LimitOrderBook

# simply use this class like it is a dictionary, it will store data automatically
class Database():
    def __init__(self, filename = './db.pkl') -> None:
        self.db = None
        self.filename = filename
        self.load_data()

    def turn_bytes_into_db(self, b: bytes):
        self.db = pickle.loads(b)
        self.store_data()
        
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
                "client_balance": defaultdict(int)
            }
        return self.db
    
    def __setitem__(self, key, value):
        self.db[key] = value
        self.store_data()

    def __delitem__(self, key):
        del self.db[key]
        self.store_data()
    
    def __getitem__(self, key):
        return self.db[key]

    def __len__(self):
        return len(self.db)

    def keys(self):
        return self.db.keys()

    def values(self):
        return self.db.values()
    
    def items(self):
        return self.db.items()