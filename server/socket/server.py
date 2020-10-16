import datetime
import selectors
import socket
import threading
import time

from common.db.db_handler import transaction
from common.observer.event_manager import CONNECT_CLIENT_EVENT, call_handler, DISCONNECTED_CLIENT_EVENT
from common.protocol.message import Header, Message, FULL_CONN, HEARTBEAT
from common.protocol.message_handler import receive_message, send_message
from server.socket.persist.client_pc_dao_maria_db import select_client_pc_by_ip, insert_client_pc, update_client_pc


class Client:

    def __init__(self,
                 address: str,
                 connection: socket.socket):
        self.address = address
        self.connection = connection
        self.last_receive_time = None
        self.__state = 0  # IDLE 0, WORKING 1, DISCONNECTED 2
        self.wait_count = 0

        self.__lock = threading.Lock()

    @property
    def state(self):
        return self.__state

    @state.setter
    def state(self, value: int):
        with threading.Lock():
            self.__state = value

    @property
    def ip(self):
        return self.address[0]

    @property
    def port(self):
        return self.address[1]

    def send(self, message: bytes):
        with self.__lock:
            self.connection.sendall(message)

    def receive(self, buffer_size=1024):
        return self.connection.recv(buffer_size)

    def close(self):
        self.connection.close()

    def __eq__(self, other):
        if isinstance(other, Client):
            return other.address == self.address
        return NotImplemented


class Server:

    def __init__(self):
        self.__config = None
        self.__client_sequence = 0
        self.__sel = None

        self.clients = []
        self.lock_clients = threading.RLock()

        self.__monitor_task = None
        self.__server_socket = None

        self.db_connector = None
        self.is_running = False

    @property
    def host(self) -> str:
        return socket.gethostbyname(socket.getfqdn())

    @property
    def port(self) -> str:
        return self.__config['port']

    @property
    def max_client(self) -> int:
        return self.__config['max_client']

    @property
    def wait_term(self) -> int:
        return self.__config['wait_term']

    @property
    def max_wait_count(self) -> int:
        return self.__config['max_wait_count']

    @staticmethod
    def __valid_property(**kwargs) -> dict:

        def raise_require_property(property_name):
            raise Exception("설정 값 '{}' 필요합니다".format(property_name))

        def raise_invalid_value_property(property_name):
            raise Exception("설정 값 '{}' 올바르지 않습니다".format(property_name))

        if not 'port' in kwargs:
            raise_require_property('port')
        elif not type(kwargs['port']) is int:
            raise_invalid_value_property('port')

        port = kwargs['port']

        if 'max_client' in kwargs and not type(kwargs['max_client']) is int:
            raise_invalid_value_property('max_client')

        max_client = kwargs['max_client'] if 'max_client' in kwargs else 10

        if 'wait_term' in kwargs and not type(kwargs['wait_term']) is int:
            raise_invalid_value_property('wait_term')

        wait_term = kwargs['wait_term'] if 'wait_term' in kwargs else 60

        if 'max_wait_count' in kwargs and not type(kwargs['max_wait_count']) is int:
            raise_invalid_value_property('max_wait_count')

        max_wait_count = kwargs['max_wait_count'] if 'max_wait_count' in kwargs else 10

        return {
            'port': port,
            'max_client': max_client,
            'wait_term': wait_term,
            'max_wait_count': max_wait_count
        }

    def start(self, **kwargs):


        if self.is_running:
            raise Exception('서버가 이미 실행중입니다.')

        try:
            self.__config = self.__valid_property(**kwargs)

            self.__socket_open()
            self.__sel = selectors.DefaultSelector()
            self.__sel.register(self.__server_socket, selectors.EVENT_READ, {'event_code': 0})

            self.clients = []
            self.is_running = True

            self.__monitor_task = threading.Thread(target=self.__monitor_clients)
            self.__monitor_task.start()

            print('서버 시작 ip : {} protocol port : {}'.format(self.host, self.port))

            self.__listen_clients()

        except Exception as e:
            print(e)
            self.stop()

    def __socket_open(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(self.max_client)
        server_socket.setblocking(False)

        self.__server_socket = server_socket

    def stop(self):

        if self.__server_socket is not None:
            self.__server_socket.close()

        self.is_running = False

        print('서버 종료')

    def __listen_clients(self):

        if not self.is_running:
            raise Exception('서버가 시작되지 않았습니다')

        while self.is_running:

            events = self.__sel.select()

            for key, _ in events:
                event_code = key.data['event_code']
                if event_code == 0:  # client 연결 요청
                    self.__accept_client()
                elif event_code == 1:  # client 메시지 수신
                    self.__receive_client_message(key.data['target'])

    def __receive_client_message(self, client: Client):
        try:
            client.last_receive_time = time.time()
            client.wait_count = 0
            header_bytes = client.receive(16)

            if not header_bytes:
                self.__disconnect_client(client)
                return

            header = Header.decode(header_bytes)
            body_bytes = client.receive(header.SIZE)

            receive_message(client, Message(header, body_bytes))

        except socket.error:
            self.__disconnect_client(client)

    def __accept_client(self):
        connection, address = self.__server_socket.accept()
        connection.setblocking(False)
        client = Client(address, connection)

        with self.lock_clients:
            try:
                if len(self.clients) != self.max_client:

                    self.__sel.register(client.connection, selectors.EVENT_READ, {'event_code': 1, 'target': client})
                    self.clients.append(client)

                    self.__handle_connect_client(client)
                    call_handler(CONNECT_CLIENT_EVENT, client=client)
                else:
                    send_message(FULL_CONN, client)
            except socket.error:
                self.__break_client(client)

    def __break_client(self, client: Client):
        with self.lock_clients:
            client = self.clients.pop(self.clients.index(client))
            self.__sel.unregister(client.connection)

            client.close()

    def __disconnect_client(self, client: Client):
        call_handler(DISCONNECTED_CLIENT_EVENT, client=client)
        self.__handle_disconnect_client(client)
        self.__break_client(client)

    def __monitor_clients(self):
        while self.is_running:
            time.sleep(self.wait_term)
            now = time.time()

            with self.lock_clients:
                for client in self.clients:
                    try:
                        if client.last_receive_time is None or int(
                                abs(now - client.last_receive_time)) > self.wait_term:

                            if client.wait_count == self.max_wait_count:
                                self.__disconnect_client(client)
                            else:
                                send_message(HEARTBEAT, client)
                                client.wait_count += 1
                    except socket.error:
                        self.__disconnect_client(client)

    @transaction
    def __handle_connect_client(self, client):

        print('클라이언트 연결 완료 ip : {}'.format(client.address))
        client_pc = select_client_pc_by_ip(self.db_connector, client.ip)
        if client_pc is None:
            insert_client_pc(self.db_connector, IP=client.ip, LAST_CONNECT_DATE=datetime.datetime.now(),
                             LAST_DISCONNECT_DATE=None)
        else:
            client_pc['LAST_CONNECT_DATE'] = datetime.datetime.now()
            update_client_pc(self.db_connector, **client_pc)


    @transaction
    def __handle_disconnect_client(self, client):

        print('클라이언트 연결 종료 ip : {}'.format(client.address))

        client_pc = select_client_pc_by_ip(self.db_connector, client.ip)
        client_pc['LAST_DISCONNECT_DATE'] = datetime.datetime.now()
        client_pc['DISCONNECT_COUNT'] += 1
        update_client_pc(self.db_connector, **client_pc)



