from common.db.db_handler import MariaDBHandler


def insert_client_pc(connector: MariaDBHandler, **client_pc):
    SQL = "INSERT INTO CLIENT_PC(IP, LAST_CONNECT_DATE, LAST_DISCONNECT_DATE) VALUES(%s, %s, %s)"
    connector.cursor.execute(SQL, (
        client_pc['IP'], client_pc['LAST_CONNECT_DATE'],
        MariaDBHandler.get_datetime_db_format(client_pc['LAST_DISCONNECT_DATE']) if client_pc[
            'LAST_DISCONNECT_DATE'] else None))


def select_client_pc_by_ip(connector: MariaDBHandler, ip: str):
    connector.cursor.execute("SELECT * FROM CLIENT_PC WHERE IP = %s", (ip))
    result = connector.cursor.fetchall()

    return None if len(result) == 0 else result[0]


def update_client_pc(connector: MariaDBHandler, **client_pc):
    connector.cursor.execute("""UPDATE CLIENT_PC SET IP = %s, LAST_CONNECT_DATE = %s, LAST_DISCONNECT_DATE = %s, 
                DISCONNECT_COUNT = %s WHERE IP = %s""",
                             (client_pc['IP'], MariaDBHandler.get_datetime_db_format(client_pc['LAST_CONNECT_DATE']),
                              MariaDBHandler.get_datetime_db_format(
                                  client_pc['LAST_DISCONNECT_DATE']) if client_pc['LAST_DISCONNECT_DATE'] else None,
                              client_pc['DISCONNECT_COUNT'], client_pc['IP']))