import pymysql
import datetime

from abc import *


class Connector(metaclass=ABCMeta):
    def __init__(self):
        self.connection = None


def transaction(func):
    def wrapper(*args, **kwargs):

        from server import MainServer

        if type(MainServer.db_connector) is MariaDBHandler:
            try:
                MainServer.db_connector.connection.begin()
                func(*args, **kwargs)
                MainServer.db_connector.connection.commit()
            except Exception as e:
                print(e)
                MainServer.db_connector.connection.rollback()
        else:
            pass

    return wrapper


class MariaDBHandler(Connector):

    def __init__(self, host, user, password, db_name):
        self.connection = pymysql.connect(host=host, user=user, password=password, db=db_name, charset='utf8')
        self.cursor = self.connection.cursor(pymysql.cursors.DictCursor)

    @classmethod
    def get_datetime_db_format(cls,
                               object_datetime: datetime.datetime):
        return object_datetime.strftime('%Y-%m-%d %H:%M:%S')
