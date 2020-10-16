from common.db.db_handler import MariaDBHandler


def insert_fetch(connector: MariaDBHandler, **fetch):
    SQL = "INSERT INTO `FETCH`(FILE_NAME, FILE_EXT, FILE_SIZE, CREATOR_IP, CREATE_DATE) VALUES (%s, %s, %s, %s, %s)"
    connector.cursor.execute(SQL, (
        fetch['FILE_NAME'], fetch['FILE_EXT'], fetch['FILE_SIZE'], fetch['CREATOR_IP'], fetch['CREATE_DATE']))

    return connector.cursor.lastrowid


def insert_fetch_result(connector: MariaDBHandler, **fetch_result):
    connector.cursor.execute("INSERT INTO FETCH_RESULT VALUES(%s, %s, %s, %s, %s)", (
        fetch_result['FETCH_ID'], fetch_result['FETCHER_IP'], fetch_result['START_DATE'],
        fetch_result['END_DATE'], fetch_result['COMPLETE_FLAG']))


def insert_fetch_fail_cause(connector: MariaDBHandler, **fetch_fail_cause):
    SQL = "INSERT INTO FETCH_FAIL_CAUSE VALUES(%s, %s, %s, %s, %s)"
    connector.cursor.execute(SQL, (
        fetch_fail_cause['FETCH_ID'], fetch_fail_cause['FETCHER_IP'],
        MariaDBHandler.get_datetime_db_format(fetch_fail_cause['START_DATE']),
        fetch_fail_cause['END_DATE'], fetch_fail_cause['CAUSE_TYPE']))
