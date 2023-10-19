import pymongo


class MongoConnector:
    def __init__(self):
        self.client = None
        self.connection_string: str = ''
        self.db = None
        self.db_table = None
        return

    def set_connection_string(self, username: str, password: str, cluster_link: str):
        self.connection_string = rf"mongodb+srv://{username}:{password}@{cluster_link}/"
        return

    def connect_client(self):
        self.client = pymongo.MongoClient(self.connection_string)
        return

    def close_connection(self):
        self.client.close()
        return

    def connect_db(self, database: str):
        db = self.client[database]
        return db

    def connect_table(self, database: str, collection: str):
        db = self.connect_db(database)
        table = db[collection]
        return table

