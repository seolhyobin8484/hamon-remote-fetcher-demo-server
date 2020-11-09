import pymysql
import datetime
import traceback

from abc import *


class Connector(metaclass=ABCMeta):
    def __init__(self):
        self.connection = None


def transaction(func):
    """
    트랜젝션 데코레이터

    DB 별 odbc 트랜젝션 함수를 사용할 수 있음

    todo: 트랜젝션 겹침 상황에 대한 처리가 미구현, 겹침 발생시 마지막 BEGIN된 함수만 트랜젝션을 처리하고 있음
    
    :현재 제공 DB
    MariaDB(pymysql)

    :param func: 
    :return: 
    """
    def wrapper(*args, **kwargs):

        from server import MainServer

        if type(MainServer.db_connector) is MariaDBHandler:
            # 사용하는 DB가 Maria DB인 경우 pymysql 트랜잭션 처리 함수 사용
            # todo: DB 당 트랜젝션 코드를 이곳에 다 적는게 아닌 Connector transaction() 함수를 만들고 오버라이딩 구현으로 DB당 트랜젝션 처리를 하도록 해야할듯
            
            try:
                MainServer.db_connector.connection.begin()
                data = func(*args, **kwargs)
                MainServer.db_connector.connection.commit()
            except Exception as e:
                MainServer.db_connector.connection.rollback()
                raise e
            else:
                return data
        else:
            pass

    return wrapper


class MariaDBHandler(Connector):

    def __init__(self, host, user, password, db_name):
        super().__init__()
        self.connection = pymysql.connect(host=host, user=user, password=password, db=db_name, charset='utf8')
        self.cursor = self.connection.cursor(pymysql.cursors.DictCursor)

    @classmethod
    def get_datetime_db_format(cls,
                               object_datetime: datetime.datetime):
        return object_datetime.strftime('%Y-%m-%d %H:%M:%S')
