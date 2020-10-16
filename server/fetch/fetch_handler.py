import datetime
import json
import threading
from queue import Queue

from common.db.db_handler import transaction
from common.observer.event_manager import DISCONNECTED_CLIENT_EVENT, register_handler, event_handler
from common.protocol.message import Message, ORDER_FETCH, RESULT_FETCH, RESULT_SEND_FILE, SEND_FILE
from common.protocol.message_handler import MessageReceiver, send_message
from server import MainServer
from server.fetch.persist.fetch_dao_maria_db import insert_fetch, insert_fetch_result, insert_fetch_fail_cause

"""

# CLIENT STATE

IDLE 0
FETCHING 1
FAIL 2
SUCCESS 3


# FAIL FETCH CAUSE

CAUSE_DISCONNECT_CLIENT = 0
CAUSE_FAIL_SEND_FILE = 1

"""


class Fetch:
    def __init__(self,
                 id: int,
                 target: list,
                 checksum: int,
                 file):
        self.id = id
        self.target = target
        self.checksum = checksum
        self.file = file

    @property
    def file_binary(self):
        return self.file['binary']

    @property
    def file_name(self):
        return self.file['name']

    @property
    def file_size(self):
        return self.file['size']

    @property
    def file_ext(self):
        return self.file['ext']

    @property
    def is_finish(self):
        fetching_client_count = 0
        for fetch_client in self.target:
            if fetch_client.state == 1:
                fetching_client_count += 1
        return fetching_client_count == 0


class FetchClient:
    def __init__(self, client):
        self.client = client
        self.__state = 0
        self.start_date = None
        self.fail_receive_file_count = 0
        self.task = None

    @property
    def state(self):
        return self.__state

    @state.setter
    def state(self, value):
        self.__state = value
        if value == 1:
            self.client.state = 1
        elif value == 2 or value == 3:
            self.client.state = 0

    @property
    def ip(self):
        return self.client.ip


class FetchHandler(MessageReceiver):

    def __init__(self):
        super().__init__()
        
        self.is_fetching = False
        self.current_fetch = None

        self.wait_queue = Queue()

        register_handler(DISCONNECTED_CLIENT_EVENT, self.__check_disconnect_client)

    def is_message_take(self, message: Message) -> bool:
        return message.HEADER.CODE == ORDER_FETCH or message.HEADER.CODE == RESULT_FETCH or message.HEADER.CODE == RESULT_SEND_FILE

    def receive(self, message: Message, client):

        json_data = json.loads(message.BODY.decode('utf-8'))

        if message.HEADER.CODE == ORDER_FETCH:
            self.__receive_order_fetch(message.HEADER.SENDER, json_data)
        elif message.HEADER.CODE == RESULT_FETCH:
            self.__receive_fetch_result(message.HEADER.SENDER, json_data)
        elif message.HEADER.CODE == RESULT_SEND_FILE:
            self.__receive_send_file_result(message.HEADER.SENDER, json_data)

    @event_handler
    def __check_disconnect_client(self, event):
        # todo 어떻게 할 건지 생각해보기
        pass

    @transaction
    def __receive_order_fetch(self, sender_ip, data):

        # sender 제외
        target = []

        with MainServer.lock_clients:
            for client in MainServer.clients:
                if data['target'] != 'all':
                    if client.ip in data['target']:
                        target.append(FetchClient(client))
                else:
                    if client.ip != data['creator_ip'] and client.ip != sender_ip:
                        target.append(FetchClient(client))

        fetch_id = insert_fetch(MainServer.db_connector,
                                FILE_NAME=data['file']['name'], CREATE_DATE=data['create_date'],
                                FILE_SIZE=data['file']['size'], CREATOR_IP=data['creator_ip'],
                                FILE_EXT=data['file']['ext'])

        fetch = Fetch(fetch_id, target, data['checksum'],
                      data['file'])

        if not self.is_fetching:
            self.current_fetch = fetch
            self.__fetch()
        else:
            self.wait_queue.put(fetch)

    def __receive_fetch_result(self, sender_ip, data):

        fetch_client = None
        for fc in self.current_fetch.target:
            if fc.ip == sender_ip:
                fetch_client = fc
                break

        if data["is_complete"]:
            self.__write_success_fetch_result(fetch_client, data["end_date"])
        else:
            self.__write_fail_fetch_result(fetch_client, data["end_date"], data["fail_cause"])

    def __receive_send_file_result(self, sender_ip, data):
        if not data['is_send_complete']:
            fetch_client = next((x for x in self.current_fetch.target if x.ip == sender_ip), None)
            fetch_client.fail_receive_file_count += 1

            if fetch_client.fail_receive_file_coune == 2:  # 파일 재전송
                send_message(SEND_FILE, fetch_client.client, json.dumps({
                    "fetch_id": self.current_fetch.id,
                    "checksum": self.current_fetch.checksum,
                    "file": self.current_fetch.file
                }).encode('utf-8'))
            else:
                self.__write_fail_fetch_result(fetch_client, datetime.datetime.now(), 1)

    def __client_fetch(self, fetch_client):
        try:
            send_message(SEND_FILE, fetch_client.client, (json.dumps({
                "fetch_id": self.current_fetch.id,
                "checksum": self.current_fetch.checksum,
                "file": self.current_fetch.file
            })).encode('utf-8'))
        except:
            self.__write_fail_fetch_result(fetch_client, datetime.datetime.now(), 0)

    def __fetch(self):

        self.is_fetching = True

        for fetch_client in self.current_fetch.target:
            fetch_client: FetchClient

            fetch_client.start_date = datetime.datetime.now()

            if fetch_client.client.state == 2:  # 파일 패티 전송 시간/대시 시간 에 따른 클라이언트 상태 변경 대비
                self.__write_fail_fetch_result(fetch_client, datetime.datetime.now(), 0)
                self.current_fetch.target.remove(fetch_client)
                continue

            fetch_client.state = 1
            fetch_client.task = threading.Thread(target=self.__client_fetch, args=(fetch_client,))  # 데이터 수정 필요
            fetch_client.task.start()

    @transaction
    def __write_success_fetch_result(self, fetch_client: FetchClient, end_date):
        fetch_client.state = 3
        insert_fetch_result(MainServer.db_connector, FETCH_ID=self.current_fetch.id, FETCHER_IP=fetch_client.ip,
                            START_DATE=fetch_client.start_date,
                            END_DATE=end_date, COMPLETE_FLAG=1)

        self.__dispose_client_finish_fetch()

    @transaction
    def __write_fail_fetch_result(self, fetch_client: FetchClient, end_date, cause):
        fetch_client.state = 2

        insert_fetch_result(MainServer.db_connector, FETCH_ID=self.current_fetch.id, FETCHER_IP=fetch_client.ip,
                            START_DATE=fetch_client.start_date,
                            END_DATE=end_date, COMPLETE_FLAG=0)

        insert_fetch_fail_cause(MainServer.db_connector, FETCH_ID=self.current_fetch.id, FETCHER_IP=fetch_client.ip,
                                START_DATE=fetch_client.start_date,
                                END_DATE=end_date, CAUSE_TYPE=cause)

        self.__dispose_client_finish_fetch()

    def __dispose_client_finish_fetch(self):
        if self.current_fetch.is_finish:  # 모든 클라이언트 패치 결과가 나왔다면
            self.current_fetch = None
            if self.wait_queue.qsize() != 0:
                self.current_fetch = self.wait_queue.get()
                self.__fetch()

