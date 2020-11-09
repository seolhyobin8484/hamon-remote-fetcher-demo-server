from common.db.db_handler import MariaDBHandler
from server import MainServer

if __name__ == "__main__":
    MainServer.db_connector = MariaDBHandler(host='127.0.0.1', user='root', password='ntflow', db_name='hamon_fetcher')
    MainServer.start(port=14494, max_client=10, max_wait_count=3)