from common.db.db_handler import MariaDBHandler


# fetch
def insert_fetch(connector: MariaDBHandler, **fetch):
    """
    패치 정보를 DB insert

    :param connector:
    :param fetch:

    fetch['FETCH_FILE_NO']: int -> 패치 파일 id(`fetch_file` fk)
    fetch['SENDER_IP']: str -> 패치 요청자 ip(`client` fk)
    fetch['START_DATE']: datetime -> 패치 시작 시각
    :return: `fetch` id(PK)
    """
    connector.cursor.execute(
        "INSERT INTO `FETCH`(FETCH_FILE_NO, SENDER_IP, START_DATE) "
        "VALUES (%s, %s, %s)", (
            fetch['FETCH_FILE_NO'], fetch['SENDER_IP'], fetch['START_DATE']))
    return connector.cursor.lastrowid


# client_fetch
def insert_client_fetch(connector: MariaDBHandler, **client_fetch):
    """
    클라이언트 패치 정보 DB insert

    :param connector:
    :param client_fetch:

    client_fetch['FETCH_NO']: int -> 담당 패치 id(`fetch` fk)
    client_fetch['IP']: str -> 클라이언트 ip(`client` fk)
    client_fetch['PATH']: str -> 패치 경로
    :return:
    """
    connector.cursor.execute(
        "INSERT INTO CLIENT_FETCH(FETCH_NO, IP, PATH) VALUES (%s, %s, %s)",
        (client_fetch['FETCH_NO'], client_fetch['IP'], client_fetch['PATH'])
    )


# fetch_result
def insert_fetch_result(connector: MariaDBHandler, **fetch_result):
    """
    패치 결과 DB 저장

    패치 성공시 fetch_result['SUCCESS_FLAG'] == True
    패치 실패시 fetch_result['SUCCESS_FLAG'] == False

    :param connector: 
    :param fetch_result:

    fetch_result['FETCH_NO']: int -> 패치 id(`fetch` fk)
    fetch_result['TARGET_IP']: str -> 패치한 클라이언트 ip(`client` fk)
    fetch_result['END_DATE']: datetime -> 패치 종료 시각
    fetch_result['SUCCESS_FLAG']: bool -> 패치 성공 여부
    :return: 
    """
    connector.cursor.execute(
        "INSERT INTO FETCH_RESULT(FETCH_NO, TARGET_IP, END_DATE, SUCCESS_FLAG) VALUES (%s, %s, %s, %s)", (
            fetch_result['FETCH_NO'], fetch_result['TARGET_IP'], fetch_result['END_DATE'],
            fetch_result['SUCCESS_FLAG']))


# fetch_fail
def insert_fetch_fail_cause(connector: MariaDBHandler, **fetch_fail_cause):
    """
    패치가 실패했을 경우 패치 실패 원인 DB 저장

    fetch_fail_cause['CAUSE_TYPE']

    클라이언트 중간 종료 = 0
    클라이언트 잘못된 파일 전송 = 1

    :param connector: 
    :param fetch_fail_cause:

    fetch_fail_cause['FETCH_NO']: int -> 패치 id(`fetch` fk)
    fetch_fail_cause['TARGET_IP']: str -> 패치한 클라이언트 ip(`client` fk)
    fetch_fail_cause['CAUSE_TYPE']: int -> 패치 원인 코드 값
    :return:
    """
    connector.cursor.execute(
        "INSERT INTO FETCH_FAIL_CAUSE(FETCH_NO, TARGET_IP, CAUSE_TYPE) VALUES (%s, %s, %s)", (
            fetch_fail_cause['FETCH_NO'], fetch_fail_cause['TARGET_IP'], fetch_fail_cause['CAUSE_TYPE']))


# fetch_file
def insert_fetch_file(connector: MariaDBHandler, **fetch_file):
    """
    패치 파일 정보 DB 저장
    
    :param connector:
    :param fetch_file:

    fetch_file['FILE_NAME']: str -> 패치 파일 이름
    fetch_file['FILE_EXT']: str -> 패치 파일 확장자
    fetch_file['FILE_SIZE']: int -> 패치 파일 크기
    fetch_file['FILE_MD5']: int -> 패치 파일 checksum
    fetch_file['CREATOR_IP']: str -> 패치 파일 생성자 ip (`client` pk)
    fetch_file['CREATE_DATE']: datetime -> 패치 파일 생성 시각

    :return:
    """
    connector.cursor.execute(
        "INSERT INTO FETCH_FILE(FILE_NAME, FILE_EXT, FILE_SIZE, FILE_MD5, CREATOR_IP, CREATE_DATE) VALUES (%s, %s, "
        "%s, %s, %s, %s)", (
            fetch_file['FILE_NAME'], fetch_file['FILE_EXT'], fetch_file['FILE_SIZE'], fetch_file['FILE_MD5'],
            fetch_file['CREATOR_IP'], fetch_file['CREATE_DATE']))
    return connector.cursor.lastrowid


def update_fetch_file(connector: MariaDBHandler, file_no, **fetch_file):
    """
    패치 파일 변경
    
    :param connector: 
    :param file_no: 
    :param fetch_file:

    fetch_file['FILE_NAME']: str -> 패치 파일 이름
    fetch_file['FILE_EXT']: str -> 패치 파일 확장자
    fetch_file['FILE_SIZE']: int -> 패치 파일 크기
    fetch_file['FILE_MD5']: int -> 패치 파일 checksum
    fetch_file['CREATOR_IP']: str -> 패치 파일 생성자 ip (`client` pk)
    fetch_file['CREATE_DATE']: datetime -> 패치 파일 생성 시각
    :return: 
    """
    connector.cursor.execute(
        "UPDATE FETCH_FILE SET FILE_NAME = %s, FILE_EXT = %s, FILE_SIZE = %s, CREATOR_IP = %s WHERE FILE_NO = %s"
        "FILE_MD5 = %s", (fetch_file['FILE_NAME'], fetch_file['FILE_EXT'], fetch_file['FILE_SIZE'],
                          fetch_file['FILE_MD5'], file_no))
