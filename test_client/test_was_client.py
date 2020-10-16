import server
import threading
import json
import struct
import base64
import datetime
import os


# code - 1byte
# sender - 4byte
# receiver - 4byte
# size - 4byte
# total : 13byte

# data is always json-format


TEST_PACKET = 0x00
CLIENT_WELCOME = 0x01
FULL_CONN = 0x02
ECHO = 0x03
ORDER_FETCH = 0x04
RESULT_FETCH = 0x05
HEARTBEAT = 0x06
RESULT_SEND_FILE = 0x07
SEND_FILE = 0x08
REQUEST_CONNECT_CLIENTS_STATE = 0x09


# INSTALL = 0x05
# BYE = 0x06
# REQUEST_CLIENTS_STATE = 0x07
# RESPONSE_CLIENTS_STATE = 0x08
# ADMIN_WELCOME = 0x09
# HEARTBEAT = 0x0A


class Header:
    def __init__(self,
                 code: int,
                 sender: str,
                 receiver: str,
                 size: int):
        self.CODE = code
        self.SENDER = sender
        self.RECEIVER = receiver
        self.SIZE = size

    @classmethod
    def decode(cls, byte_data):
        header = struct.unpack('B4B4BL', byte_data[0:16])

        code = header[0]
        sender = '.'.join(list(map(str, header[1:5])))
        receiver = '.'.join(list(map(str, header[5:9])))
        size = header[9]

        return Header(code, sender, receiver, size)

    @classmethod
    def encode(cls, packet) -> bytes:
        get_ip = lambda ip: [int(piece) for piece in ip.split('.')]

        sender_ip_pieces = get_ip(packet.SENDER)
        receiver_ip_pieces = get_ip(packet.RECEIVER)

        header = struct.pack('B4B4BL', packet.CODE, *sender_ip_pieces, *receiver_ip_pieces, packet.SIZE)

        return header


class Message:

    def __init__(self,
                 header: Header,
                 body: bytes):
        self.HEADER = header
        self.BODY = body


def send_message(code: int,
                 ip,
                 conn,
                 body=None):
    header = Header(code, server.gethostbyname(server.getfqdn()), ip, 0 if body is None else len(body))
    data = Header.encode(header)

    print(data)
    print(body)

    if body:
        data += body

    conn.sendall(data)


HOST = '10.1.2.171'
PORT = 14454


class TestClient:
    def __init__(self):
        self.is_running = False
        self.client_socket = None
        self.thread = None
        self.my_id = None

    @property
    def my_ip(self):
        return server.gethostbyname(server.getfqdn())

    def start(self):
        client_socket = server.socket(server.AF_INET, server.SOCK_STREAM)
        client_socket.connect((HOST, PORT))

        print('서버 연결 성공')

        self.is_running = True
        self.client_socket = client_socket

        thread = threading.Thread(target=self.receive)
        thread.start()

        self.thread = thread

        try:
            while True:
                print('▒' * 20)
                print('작업 을 선택하여 주세요')
                print('1. 클라이언트 연결 상태 확인')
                print('2. 파일 전송')
                print('▒' * 20)
                choice = int(input(">>>"))
                print()

                if choice == 1:
                    send_message(REQUEST_CONNECT_CLIENTS_STATE, '10.1.2.171', server)
                elif choice == 2:
                    print('전송하고자 하는 파일의 경로를 입력하여 주세요')
                    file_path = input(">>>")

                    file_full_name = file_path[file_path.rindex('/') + 1:]
                    file_name, file_ext = file_full_name.split('.')
                    file_size = os.path.getsize(file_path)

                    print(file_name, file_ext, file_size)

                    with open(file_path, 'rb') as file:
                        encoding_binary = base64.b64encode(file.read())
                        send_json_data = json.dumps({
                            "checksum": 77,
                            "target": 'all',
                            "creator_ip": self.my_ip,
                            "create_date": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "file": {
                                "name": file_name,
                                "ext": file_ext,
                                "size": file_size,
                                "binary": encoding_binary.decode('utf-8')
                            }
                        })

                        send_message(ORDER_FETCH, '10.1.2.171', client_socket, send_json_data.encode('utf-8'))
        except KeyboardInterrupt:
            self.close()

        print('server is closed')

    def receive(self):
        while self.is_running:
            data = self.client_socket.recv(1024)

            if not data:
                self.close()
                return

            message = Message.decode(data)
            print("protocol received code is {} sender is {} receiver is {} size is {}".format(message.code,
                                                                                              message.sender,
                                                                                              message.receiver,
                                                                                              message.size))

            if message.code == HEARTBEAT:
                print('heartbeat')

    def close(self):
        self.is_running = False
        self.client_socket.close()
        print('server is closed')
        exit(0)


client = TestClient()
client.start()
