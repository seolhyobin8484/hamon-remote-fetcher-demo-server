import datetime
import json
from collections import UserDict

from common.db.db_handler import transaction
from event import EventManager
from event.event_manager import DISCONNECTED_CLIENT_EVENT, event_handler
from common.protocol.message import Message, ORDER_FETCH, RESULT_FETCH, RESULT_SEND_FILE, SEND_FILE, \
    RESULT_PREPARE_FETCH, \
    REQUEST_CLIENT_STATE, RESPONSE_CLIENT_STATE
from common.protocol.message_handler import MessageReceiver, send_message, \
    multi_send_message
from server import MainServer
from server.fetch.persist.fetch_dao_maria_db import insert_fetch, insert_fetch_file, insert_fetch_result, \
    insert_fetch_fail_cause, insert_client_fetch
from server.socket.client import Client


class FileFetch:
    """
    패치 정보 DTO
    """

    def __init__(self, no, file, workers):
        self.no: int  # 파일 패치 id
        self.FILE: dict
        self.workers: list
        """
        패치할 클라이언 마다 필요한 정보를 리스트로 담고 있음 (dict 타입)
        해당 정보는 클라이언트가 패치를 진행되고 있을동안만 유지하고 있으며 실패/성공한 경우
        바로 삭제된다.
        
        worker = workers[n]
        worker['client']: 클라이언트 래퍼 객체
        worker['path']: 클라이언트 패치 경로   
        """

        self.no = no
        self.FILE = file
        self.workers = workers

    @property
    def file(self):
        return self.FILE

    @property
    def file_no(self):
        """
        :return: 패치 파일 id
        """
        return self.FILE['no']

    @property
    def file_md5(self):
        """        
        :return: 패치 파일 md5(checkusm) 
        """
        return self.FILE['md5']

    @property
    def file_name(self):
        """
        :return: 패치 파일 이름 
        """
        return self.FILE['name']

    @property
    def file_ext(self):
        """
        :return: 패치 파일 확장자 
        """
        return self.FILE['ext']

    @property
    def file_size(self):
        """
        :return: 패치 파일 크기
        """
        return self.FILE['size']

    @property
    def is_finish(self):
        """
        해당 패치가 모두 진행되었는지 확인
        성공/실패를 떠나서 모든 클라이언트가 패치 완료되었다면 진행 완료 상태로 알림
        
        :return: 패치 진행 완료 -> True, 패치 진행 실패 -> False
        """
        return len(self.workers) == 0


class FileFetchDict(UserDict):
    """
    동시에 여러 패치를 진행 하기 위해 여러 요청에 대해서
    필요한 패치 정보를 쉽게 가져올 수 있도록 하기 위해 만든 커스텀 딕셔너리 클래스
    """

    def __contains__(self, key: int):
        return key in self.data

    def __setitem__(self, key, value: FileFetch):
        """
        :param key: fetch.no
        :param value: 파일 패치 정보 객체
        :return:
        """
        if not isinstance(value, FileFetch):
            raise TypeError

        self.data[key] = value

    def __getitem__(self, key) -> FileFetch:
        """
        :param key: [int, FileFetch, Client]

        if type(key)

        int -> 파일 패치 id
        FileFetch -> 파일 패치 객체, no 속성 접근해 패치 id로 다시 찾음
        Client -> 클라이언트 통신 객체, 클라이언트가 속한 FileFetch 객체를 찾아 리턴
        클라이언트는 오직 하나의 패치밖에 진행못하므로 여러 FileFetch 에 저장되어 있는 경우는 없음

        :return: 필요한 FileFetch 없을 시 예외 발생
        """
        if isinstance(key, Client):
            for fetch in self.data.values():
                fetch: FileFetch

                if key in fetch.workers:
                    return fetch
        elif isinstance(key, FileFetch):
            return self.data[key.no]
        return self.data[key]

    def finish(self, client):
        """
        받아온 클라이언트가 속한 FileFetch 객체를 찾아 완료 처리를 함
        만약에 모든 클라이언트가 끝맞춰 패치가 완료된 상태라면 해당 딕셔너리에서 삭제
        :param client: Client 패치 종료된 클라이언트
        :return:
        """
        fetch = self[client]

        del fetch.workers[client]

        if fetch.is_finish:
            del self.data[fetch.no]

        return fetch


class FetchHandler(MessageReceiver):
    """
    파일 패치 관련 메시지를 수신/전송하고 컨트롤하는 헨들러 클래스

    - 동시에 여러 패치를 진행할 수 있도록 설계(단, 클라이언트는 동시에 여러 패치를 진행 못함 추후에 가능도록 할 예정)
    """

    def __init__(self):
        super().__init__()
        self.file_fetch_dict = FileFetchDict()

        EventManager.register_handler(DISCONNECTED_CLIENT_EVENT, self._check_disconnect_client)

    def is_message_take(self, message: Message) -> bool:
        """
        수신 가능 메시지 코드
        - ORDER_FETCH(4)
        - RESULT_FETCH(5)
        - RESULT_SEND_FILE(7)
        - SEND_FILE(8)
        - REQUEST_CLIENT_STATE(11)

        :param message:
        :return:
        """
        return message.HEADER.CODE == ORDER_FETCH or message.HEADER.CODE == RESULT_FETCH \
               or message.HEADER.CODE == RESULT_SEND_FILE or message.HEADER.CODE == SEND_FILE \
               or message.HEADER.CODE == REQUEST_CLIENT_STATE

    def receive(self, message: Message, client: Client):

        if message.HEADER.CODE == ORDER_FETCH:
            self._receive_order_fetch(client, message)
        elif message.HEADER.CODE == SEND_FILE:
            self._send_file(message)
        elif message.HEADER.CODE == RESULT_FETCH:
            self._receive_fetch_result(client, message)
        elif message.HEADER.CODE == REQUEST_CLIENT_STATE:
            self._client_fetch_state(client)

    @event_handler
    def _check_disconnect_client(self, event: dict):
        """
        패치중인 클라이언트가 종료될시 패치 실패와 종료 처리

        :param event: 
        :return: 
        """
        client = event['client']

        try:
            with client:
                fetch = self.file_fetch_dict.finish(client)
        except KeyError:
            pass
        else:
            self._write_fail_fetch_result(client, fetch.no, datetime.datetime.now(), 0)

    def _receive_order_fetch(self, sender, message):
        """
        패치 준비 처리 메소드
        
        시간 차에 문제로 요청 전후에 따라 클라이언트 상태 변경으로 패치를 받지 못하는 클라이언트들이 생겨날 수 있음
        연결된 클라이언트들만 패치를 진행하는 방법으로도 갈 수 있었지만 패치 요청자가 시작을 원하지 않을 수 있으므로
        패치 준비 실패 메시지를 보내, 패치 요청 다시 할것을 권유하도록 함

        패치 준비 실패시: 파일 제공자(웹)에게 패치 준비 실패 메시지를 보냄 (아직 미구현)
        패치 준비 성공시: 파일 제공자(웹)에게 패치 준비 완료 메세지를 대상 클라이언트들에겐 패치 준비 요청 메세지를 전달

        
        :param sender:
        :param message: message.code == ORDER_FETCH(4)
        :return:
        """

        data = message.json_body
        """
        :type dict

        :key
        [targets]: 패치 대상 클라이언트 정보 리스트
            :element
            [ip]: 클라이언트 ip
            [path]: 클라이언트 패치 경로
        [sender_ip]: 패치 요청 ip
        [file]: 파일 정보 딕셔너리
            :key
            [no]: 파일 id, 최초 파일일 경우 None값임
            [md5]: 파일 checksum
            [name]: 파일 이름
            [ext]: 파일 확장자
            [size]: 파일 크기

        """

        file_no = data['file'].get('no', None)
        workers = {}
        fail_client_ip = []

        with MainServer.lock_clients:
            try:
                for target in data['targets']:
                    client = next((x for x in MainServer.clients if x.ip == target['ip']), None)

                    if not client or client.state == 1:
                        fail_client_ip.append(target['ip'])
                    else:
                        workers[client] = {
                            'client': client,
                            'path': target['path']
                        }

                @transaction
                def register_fetch_service() -> FileFetch:
                    """

                    최초 파일인 경우 db에 등록(파일이름, 확장자, 크기, md5, 생성 시각, 생성자)
                    패치 정보 db 저장(패치 요청자 ip, 패치 시작 시각, 패치 파일(FK))
                    대상 클라이언트들의 패치 정보 db 저장(패치 경로, ip(FK), 패치 id(FK))

                    :return:
                    """

                    if not file_no:
                        # 파일 id 값이 없을 경우 최초 파일로 인식하고 db에 넘어온 파일 정보를 저장
                        data['file']['no'] = insert_fetch_file(MainServer.db_connector,
                                                               FILE_NAME=data['file']['name'],
                                                               FILE_EXT=data['file']['ext'],
                                                               FILE_SIZE=data['file']['size'],
                                                               FILE_MD5=data['file']['md5'],
                                                               CREATOR_IP=data['sender_ip'],
                                                               CREATE_DATE=datetime.datetime.now())

                    fetch_no = insert_fetch(MainServer.db_connector, FETCH_FILE_NO=data['file']['no'],
                                            SENDER_IP=data['sender_ip'],
                                            START_DATE=datetime.datetime.now())
                    # 패치 정보를 db 저장

                    for worker in workers.values():
                        insert_client_fetch(MainServer.db_connector, FETCH_NO=fetch_no, IP=worker['client'].ip,
                                            PATH=worker['path'])

                    return FileFetch(fetch_no, data['file'], workers)

                if len(fail_client_ip) != 0:
                    raise Exception('hello')

                file_fetch = register_fetch_service()

            except Exception as e:
                send_message(RESULT_PREPARE_FETCH, MainServer.host, sender, json.dumps({
                    "is_success": False,
                    'fail_clients_ip': [client_ip for client_ip in fail_client_ip]
                }).encode('utf-8'))
            else:
                self.file_fetch_dict[file_fetch.no] = file_fetch

                send_message(RESULT_PREPARE_FETCH, MainServer.host, sender, json.dumps({
                    "fetch_no": file_fetch.no,
                    "is_success": True
                }).encode('utf-8'))
                """
                파일 제공자에게 패치 준비 완료 메시지와 패치 id를 전송 후
                후에 파일 제공자(웹)은 이 id 함께 파일 바이너리 데이터를 보내야 하며 서버는 이 id 값으로 식별하여
                필요한 클라이언트들에게 전달
                """

                for worker in file_fetch.workers.values():
                    send_message(ORDER_FETCH, MainServer.host, worker['client'], json.dumps({
                        "fetch_no": file_fetch.no,
                        "fetch_file_no": file_fetch.file_no,
                        "file": file_fetch.file,
                        "path": worker["path"]
                    }).encode('utf-8'))
                # 대상 클라이언트들에게 패치 준비 요청 메시지 전송

    def _receive_fetch_result(self, sender, message):
        """
        클라이언트 패치 결과 수신 처리 메소드
        
        :param sender: 
        :param message: 
        :return: 
        """

        data = message.json_body
        """
        :type dict
        
        :key
        [fetch_no]: 패치 id
        [is_complete]: 패치 성공 여부, 성공 시 True
        [fail_cause]: 파일 실패 원인, (not require)
        """

        if data["is_complete"]:
            self._write_success_fetch_result(sender, data['fetch_no'], datetime.datetime.now())
        else:
            self._write_fail_fetch_result(sender, data['fetch_no'], datetime.datetime.now(), data["fail_cause"])

        sender.state = 0
        # 클라이언트 상태를 IDLE 로 변경

        self.file_fetch_dict.finish(sender)

    # todo: 타켓 클라이언트가 모두 종료되었을때에도 웹쪽에선 파일을 계속 보내고 있다는 문제점이 있음, 받을 클라이언트가 없을시 파일제공자(웹)는 파일 전송을 중단하도록 할 수 있는 처리 필요
    # todo: 파일 제공자(웹)가 파일을 보내고 있을때 끊어진 경우 패치 중인 클라이언트에게 실패 처리 후 패치 종료 알림 메시지 전송이 필요함
    def _send_file(self, message):

        data = message.json_body
        """
        :type dict
        
        :key
        [fetch_no]: 패치 id
        [binary]: 파일 바이너리 데이터(base64 인코딩)
        [is_final]: 마지막 파일 전송 확인 flag, 마지막 파일 전송일 경우 True
        """

        try:
            file_fetch: FileFetch
            file_fetch = self.file_fetch_dict[data['fetch_no']]
            # 패치 대상 클라이언트들을 찾기 위해 패치 id를 통해 FileFetch 객체를 찾음
        except KeyError:
            pass
        else:
            multi_send_message(SEND_FILE, MainServer.host, file_fetch.workers, message.BODY)

    @transaction
    def _write_success_fetch_result(self, client: Client, fetch_no: int, end_date: datetime.datetime):
        """
        클라이언트 패치 성공 처리 메소드
        
        :param client: 
        :param fetch_no: 
        :param end_date: 
        :return: 
        """
        insert_fetch_result(MainServer.db_connector, FETCH_NO=fetch_no, TARGET_IP=client.ip, END_DATE=end_date,
                            SUCCESS_FLAG=True)

    @transaction
    def _write_fail_fetch_result(self, client: Client, fetch_no: int, end_date: datetime.datetime, cause: int):
        """
        클라이언트 패치 실패 처리 메소드
        
        :param client: 
        :param fetch_no: 
        :param end_date: 
        :param cause:

        클라이언트 중간 종료 = 0
        클라이언트 잘못된 파일 전송 = 1

        
        :return: 
        """
        insert_fetch_result(MainServer.db_connector, FETCH_NO=fetch_no, TARGET_IP=client.ip, END_DATE=end_date,
                            SUCCESS_FLAG=False)
        insert_fetch_fail_cause(MainServer.db_connector, FETCH_NO=fetch_no, TARGET_IP=client.ip, CAUSE_TYPE=cause)

    # def _client_fetch_state(self, client):  # todo 수정 필요(구현 안됨)
    #
    #     result = []
    #     for client in MainServer.clients:
    #         json_data = {
    #             "ip": client.ip,
    #             "state": client.state
    #         }
    #
    #         if client.state == 0:
    #             fetch_client = next((x for x in self.fetch_files.target if x.ip == client.id), None)
    #             json_data["working_info"] = {
    #                 "fetch_id": self.fetch_files.id,
    #                 "state": fetch_client.state
    #             }
    #
    #         result.append(json_data)
    #
    #     send_message(RESPONSE_CLIENT_STATE, client, json.dumps(result).encode("utf-8"))
