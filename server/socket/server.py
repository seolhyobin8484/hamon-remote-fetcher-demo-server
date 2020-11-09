import datetime
import selectors
import socket
import threading
import time
import traceback
import signal
from contextlib import suppress

from common.db.db_handler import transaction, Connector
from event import EventManager
from event.event_manager import CONNECT_CLIENT_EVENT, DISCONNECTED_CLIENT_EVENT, event_handler
from common.protocol.message import Header, Message, FULL_CONN, HEARTBEAT
from common.protocol.message_handler import receive_message, send_message, make_message
from server.socket.client import Client
from server.socket.persist.client_dao_maria_db import select_client_by_ip, insert_client, update_client


class Server:
    """

    """

    def __init__(self):

        self._config: dict
        self.clients: list
        self._server_socket: socket.socket
        self.db_connector: Connector
        self.is_running: bool
        self._sel: selectors.DefaultSelector
        self.lock_clients: threading.RLock

        self._config = None
        self.clients = None
        self._server_socket = None
        self.db_connector = None
        self.is_running = False

        self._sel = None

        self.lock_clients = threading.RLock()

        EventManager.register_handler(CONNECT_CLIENT_EVENT, self._handle_connect_client)
        EventManager.register_handler(DISCONNECTED_CLIENT_EVENT, self._handle_disconnect_client)

        signal.signal(signal.SIGINT, self.stop)
        # 콘솔로 실행시 ctrl+c 이벤트를 받았을때 서버가 종료되도록 처리

    @property
    def host(self) -> str:
        return '10.1.2.171'

    @property
    def port(self) -> str:
        return self._config['port']

    @property
    def max_client(self) -> int:
        """
        최대 클라이언트 연결 수
        :return:
        """
        return self._config['max_client']

    @property
    def wait_term(self) -> int:
        """
        heartbeat 전송 수행 주기 (단위: 초)
        :return:
        """
        return self._config['wait_term']

    @property
    def max_wait_count(self) -> int:
        """
        클라이언트가 max_wait_count 만큼 heartbeart를 받고 응답이 없을시 연결을 끊습니다.
        :return:
        """
        return self._config['max_wait_count']

    @staticmethod
    def _valid_property(**kwargs: dict) -> dict:
        """
        서버 프로퍼티를 검증, 사용자가 정한 속성 값이 없을 경우 기본값으로 지정함
        속성 값이 유효하지 않거나, 필수로 지정해야 하는 속성이 없을 경우 예외를 발생 시킴

        설정 가능 속성
        [port]: int  -> (필수) 서버의 포트 값
        [max_client]: int -> 최대 클라이언트 접속 가능 수
        [wait_term]: int  -> heartbeat 전송 주기 (단위: 초)
        [max_wait_count]: int -> 최대 Heartbeat 수신 가능 수, 클라이언트가 max_wait_count 만큼 heartbeart를 받고 응답이 없을시 연결을 끊습니다.

        :param kwargs:
        :return: 
        """

        def raise_require_property(property_name):
            raise Exception("설정 값 '{}' 필요합니다".format(property_name))

        def raise_invalid_value_property(property_name):
            raise Exception("설정 값 '{}' 올바르지 않습니다".format(property_name))

        if 'port' not in kwargs:
            raise_require_property('port')
        elif not type(kwargs['port']) is int:
            raise_invalid_value_property('port')

        port = kwargs['port']

        if 'max_client' in kwargs and type(kwargs['max_client']) is not int:
            raise_invalid_value_property('max_client')

        max_client = kwargs['max_client'] if 'max_client' in kwargs else 10

        if 'wait_term' in kwargs and type(kwargs['wait_term']) is not int:
            raise_invalid_value_property('wait_term')

        wait_term = kwargs['wait_term'] if 'wait_term' in kwargs else 60

        if 'max_wait_count' in kwargs and type(kwargs['max_wait_count']) is not int:
            raise_invalid_value_property('max_wait_count')

        max_wait_count = kwargs['max_wait_count'] if 'max_wait_count' in kwargs else 10

        return {
            'port': port,
            'max_client': max_client,
            'wait_term': wait_term,
            'max_wait_count': max_wait_count
        }

    def start(self, **kwargs: dict):
        """
        서버를 실행 시키는 함수, 청취 소켓을 염, 멀티 플렉싱 서버에 맞게 select() 사용하여
        여러 클라이언트 요청 처리
        :param kwargs: 서버 속성
        :return:
        """
        if self.is_running:
            raise Exception('서버가 이미 실행중입니다.')

        try:
            self._config = self._valid_property(**kwargs)

            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(self.max_client)
            self._server_socket.setblocking(False)
            # 클라이언트 연결 요청을 select() 이용해 accept을 non-blocking으로 처리할 것이므로 blocking을 False 설정

            self._sel = selectors.DefaultSelector()
            self._sel.register(self._server_socket, selectors.EVENT_READ, None)

            self.clients = {}
            self.is_running = True

            monitor_task = threading.Thread(target=self._monitor_clients)
            monitor_task.start()

            print('서버 시작 ip : {} protocol port : {}'.format(self.host, self.port))

        except socket.error as e:
            print(e)
            traceback.print_exc()
            self.stop()

        while self.is_running:
            try:
                events = self._sel.select()
            except OSError as e:
                """
                멀티 스레드 환경으로 인해 _handle_disconnect_client() 함수에서 처리하기도 전에 selectors.select() 가 실행되어 비어있는 소켓 접근 오류가 발생되는
                문제가 발생됨, select 안에 비어있는 소켓은 무조건적으로 언젠간 해제 될것이기 때문에 이를 무시하도록 함 
                """
                pass
            else:
                for key, _ in events:
                    """
                    selectors 엔 헨들러 2가지를 등록함
                    - 클라이언트 연결 요청 (fileobj: 청취 소켓, arg: 없음)
                    - 클라이언트 메시지 수신 (fileobj: 클라이언트 통신 소켓, arg: Client 객체)
                    """
                    if key.fileobj is self._server_socket:
                        self._accept_client()
                    else:
                        self._receive_client_message(key.data)

            # with suppress(OSError):
            #     """
            #     멀티 스레드 환경으로 인해 _handle_disconnect_client() 함수에서 처리하기도 전에 selectors.select() 가 실행되어 비어있는 소켓 접근 오류가 발생되는
            #     문제가 발생됨, select 안에 비어있는 소켓은 무조건적으로 언젠간 해제 될것이기 때문에 이를 무시하도록 함 
            #     """
            #     events = self._sel.select()
            # 
            # for key, _ in events:
            #     """
            #     selectors 엔 헨들러 2가지를 등록함
            #     - 클라이언트 연결 요청 (fileobj: 청취 소켓, arg: 없음)
            #     - 클라이언트 메시지 수신 (fileobj: 클라이언트 통신 소켓, arg: Client 객체)
            #     """
            #     if key.fileobj is self._server_socket:
            #         self._accept_client()
            #     else:
            #         self._receive_client_message(key.data)

    def stop(self):

        if self._server_socket is not None:
            self._server_socket.close()

        # for client in self.clients:
        #     client.close()
        # todo : (윗코드) DB 에러가 발생함 원인은 send 스레드 해결방안 찾을것

        self.is_running = False

        print('서버 종료')

    def _accept_client(self):
        channel: socket.socket
        address: tuple

        channel, address = self._server_socket.accept()

        if len(self.clients) != self.max_client:
            client = Client(address, channel)
            # 소켓을 유용하고 편하게 사용하기 위해 Client 래퍼 객체로 생성
            try:
                self._sel.register(client.channel, selectors.EVENT_READ, client)  # selectors 이벤트 등록
                self.clients[client] = client
                # 클라이언트 리스트 등록

                EventManager.call_handler(CONNECT_CLIENT_EVENT, client=client)
            except socket.error as e: 
                # todo: (try-except) 이제 이벤트 헨들러는 개별 스레드에서 처리하므로 try-except 필요가 없음
                with client:
                    if client != 2:
                        client.close()
        else:
            # 최대 클라이언트 연결 수를 넘어갔을 경우 꽉 찼다는 메시지르 보내고 연결 종료
            channel.sendall(make_message(FULL_CONN, self.host, address[0]))
            channel.close()

    # todo: 잘못된 데이터가 넘어왔을때 처리 생각해야 함
    # todo: sendall(x) send 하고 클라 종료시 에러 발생
    def _receive_client_message(self, client: Client):
        try:
            with client:

                client.last_receive_time = time.time()
                client.wait_count = 0
                # 수신 한 경우 heartbeat 누적 수를 초기화
                # todo: Cleint receive 함수 내부에 처리할것

                header_bytes = client.receive(13)
                # 헤더 사이즈 만큼 버퍼에서 가져옴
                # todo: 사이즈가 작긴 하지만 이 부분도 아래 BODY 데이터를 가지고 오는 것처럼 처리를 해줘야함 (Client receive 함수 내에 처리)

                if not header_bytes:
                    if client.state != 2:
                        client.close()
                        EventManager.call_handler(DISCONNECTED_CLIENT_EVENT, client=client)
                    # todo: 이벤트 호출자가 제어하지 않고, 함수 안에서 실행을 제어하도록 변경
                    #   예) 클라이언트 연결 이벤트에서 헨들러 A가 실행할때 어떠한 이유로 클라이언트를 종료시킨 경우 다음 번에 실행될
                    #   (이벤트에 대한 헨들러들이 순차적으로 실행됨) 클라이언트 연결 이벤트 헨들러 B가 실행 되면 안되므로
                    return

                header = Header.decode(header_bytes)

                if not header:
                    return

                body_bytes = client.receive(header.SIZE)
                # body 크기는 가변 적이므로 header에서 body 사이즈를 알아낸 후 버퍼에서 가져옴

                while len(body_bytes) < header.SIZE:
                    body_bytes += client.receive(header.SIZE - len(body_bytes))
                # 서버 상황상 명시한 사이즈 만큼 데이터를 가지고 온다는 보장이 없으므로, 완전할때까지 버퍼에서 가져옴

                receive_message(client, Message(header, body_bytes))

        except Exception as e:
            # 연결 혹은 받아온 데이터에 문제가 있으면 연결을 끊는거로 처리하고 있음
            with client:
                if client.state != 2:
                    client.close()
                    EventManager.call_handler(DISCONNECTED_CLIENT_EVENT, client=client)
            # receive_message 에서 데이터를 잘못받아도 예외가발생

    def _monitor_clients(self):
        while self.is_running:
            time.sleep(self.wait_term)
            now = time.time()

            with self.lock_clients:
                for client in list(self.clients):
                    try:
                        with client:
                            if client.state == 2:
                                return

                            if client.last_receive_time is None or int(
                                    abs(now - client.last_receive_time)) > self.wait_term:
                                # 클라이언트의 마지막 수신 시각과 현재 시각을 비교해  heartbeat 전송 주기가 돌아오기 전까지 데이터가 수신한 적이 있는지 확인
                                if client.wait_count == self.max_wait_count:
                                    """
                                    클라이언트가 최대 heartbeat 허용 횟수를 넘긴 상태라면 연결이 끊긴 상태라고 판단하고 예외를 발생시켜 except 부분에서 클라이언트
                                    종료 처리
                                    """
                                    raise Exception
                                else:
                                    # 허용 횟수를 넘기지 않은 상태라면 heartbeat 메시지 전송 후 heartbeat 전송 횟수를 1 증가 시킴
                                    send_message(HEARTBEAT, self.host, client)
                                    client.wait_count += 1
                    except Exception as e:
                        with client:
                            if client.state != 2:
                                client.close()
                                EventManager.call_handler(DISCONNECTED_CLIENT_EVENT, client=client)

    @event_handler
    @transaction
    def _handle_connect_client(self, event):

        client = event['client']
        print('클라이언트 연결 완료 ip : {}'.format(client.address))

        client_pc = select_client_by_ip(self.db_connector, client.ip)
        # db에 등록되어 있는 클라이언트인지 확인 (pk: 클라이언트 ip)
        if client_pc is None:
            insert_client(self.db_connector, IP=client.ip, LAST_CONN_DATE=datetime.datetime.now(),
                          LAST_DISCONN_DATE=None)
        else:
            # 등록되어 있는 클라이언트라면 마지막 접속 시각(last_disconn_date)만 업데이트
            client_pc['LAST_CONN_DATE'] = datetime.datetime.now()
            update_client(self.db_connector, client_pc['IP'], **client_pc)

    @event_handler
    @transaction
    def _handle_disconnect_client(self, event):
        client = event['client']

        print('클라이언트 연결 종료 ip : {}'.format(client.address))

        self._sel.unregister(client.channel)
        del self.clients[client]
        # selectors 해당 클라이언트 등록 해제, 클라이언트 리스트에서 삭제

        client_pc = select_client_by_ip(self.db_connector, client.ip)
        client_pc['LAST_DISCONN_DATE'] = datetime.datetime.now()
        client_pc['DISCONN_CNT'] += 1
        update_client(self.db_connector, client.ip, **client_pc)
        # 마지막 접속 시각(last_disconn_date)을 현재 시각으로 업데이트 하고 disconn_cnt 1 증가 시킴
















# select() 사용한 이유는 blocking 으로 인해 여러 스레드를 사용해야만 하는 불편함을 없애기 위해(한 스레드에서 처리 할 수 있게) 하기 위함
