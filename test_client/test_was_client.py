import socket
import threading
import json
import struct
import base64
import datetime
import os
import time
import traceback

# code - 1byte
# sender - 4byte
# receiver - 4byte
# size - 4byte
# total : 13byte

# data is always json-format


TEST_PACKET = 0
CLIENT_WELCOME = 1
FULL_CONN = 2
ECHO = 3
ORDER_FETCH = 4
RESULT_FETCH = 5
HEARTBEAT = 6
RESULT_SEND_FILE = 7
SEND_FILE = 8
START_FETCH = 9
WAIT_FETCH = 10
REQUEST_CLIENT_STATE = 11
RESPONSE_CLIENT_STATE = 12
ALREADY_FETCH_ORDER = 13
TMP_CHAT = 14


# INSTALL = 0x05
# BYE = 0x06
# REQUEST_CLIENTS_STATE = 0x07
# RESPONSE_CLIENTS_STATE = 0x08
# ADMIN_WELCOME = 0x09
# HEARTBEAT = 0x0A


class Header:
    def __init__(self,
                 size: int,
                 code: int,
                 sender: str,  # 4바이트의 정수값 사용하기 0x00|00|00|00
                 receiver: str):
        self.SIZE = size
        self.CODE = code
        self.SENDER = sender
        self.RECEIVER = receiver

    @classmethod
    def decode(cls, byte_data: bytes):
        """
        bytes(len=13) -> Header 변환 함수

        :param byte_data: bytes(len=13 고정)

        size - 4byte
        code - 1byte
        sender - 1byte * 4 = 4byte
        receiver - 1byte * 4 = 4byte

        :return:
        """
        header = None
        try:
            unpack_header = struct.unpack('LB4B4B', byte_data)
            """
            L(size: unsigned long) = 4byte
            B(code: unsigned char) = 1byte     
            4B(sender: unsigned char * 4) 정수 값이 0 ~ 256 므로 = 4byte
            4B(receiver: unsigned char * 4) 정수 값이 0 ~ 256 므로 = 4byte       
            """

            print(unpack_header)

            size = unpack_header[0]
            code = unpack_header[1]
            sender = socket.inet_ntoa(byte_data[5:9])
            receiver = socket.inet_ntoa(byte_data[9:13])

            header = Header(size, code, sender, receiver)

        except Exception as e:
            print(e)

        return header

    @classmethod
    def encode(cls, header) -> bytes:
        """
        Header -> bytes 변환 함수

        :param header:
        :return:
        """
        return struct.pack('LB4B4B', header.SIZE, header.CODE, *socket.inet_aton(header.SENDER),
                           *socket.inet_aton(header.RECEIVER))


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
    header = Header(0 if body is None else len(body), code, socket.gethostbyname(socket.getfqdn()), ip)
    data = Header.encode(header)

    print("message SEND code is {} sender is {} receiver is {} size is {}".format(header.CODE,
                                                                                  header.SENDER,
                                                                                  header.RECEIVER,
                                                                                  header.SIZE))

    if body:
        data += body

    conn.sendall(data)


HOST = '10.1.2.171'
PORT = 14494


class TestClient:
    def __init__(self):
        self.is_running = False
        self.connection_socket = None
        self.thread = None
        self.my_id = None

        self.tmp_path = None
        self.current_id = None

    @property
    def my_ip(self):
        return socket.gethostbyname(socket.getfqdn())

    def start(self):

        try:
            connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connection_socket.connect((HOST, PORT))

            print('서버 연결 성공!')

            self.is_running = True
            self.connection_socket = connection_socket

            thread = threading.Thread(target=self.receive)
            thread.start()

            self.thread = thread

            while True:
                print('▒' * 20)
                print('작업 을 선택하여 주세요')
                print('1. 클라이언트 연결 상태 확인')
                print('2. 파일 전송')
                print('▒' * 20)
                choice = int(input(">>>"))
                print()

                if choice == 1:
                    pass
                    # send_message(REQUEST_CONNECT_CLIENTS_STATE, '10.1.2.171', connection_socket)
                elif choice == 2:
                    print('전송하고자 하는 파일의 경로를 입력하여 주세요')
                    self.tmp_path = input(">>>")

                    file_full_name = self.tmp_path[self.tmp_path.rindex('/') + 1:]
                    file_name, file_ext = file_full_name.split('.')
                    file_size = os.path.getsize(self.tmp_path)

                    print(file_name, file_ext, file_size)

                    send_message(ORDER_FETCH, '10.1.2.171', connection_socket, json.dumps({
                        "targets": [
                            {
                                "ip": '10.1.1.8',
                                "path": '/root'
                            },
                            # {
                            #     "ip": '10.1.1.15',
                            #     "path": '/root'
                            # },
                            # {
                            #     "ip": '10.1.1.42',
                            #     "path": '/root'
                            # },
                            # {
                            #     "ip": '10.1.2.171',
                            #     "path": '/root'
                            # }
                        ],
                        "sender_ip": self.my_ip,
                        "start_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "file": {
                            "no": None,  # None이라면 처음패치 아니라면 재전송
                            "md5": 77,
                            "name": file_name,
                            "ext": file_ext,
                            "size": file_size,
                        }
                    }).encode("utf-8"))
                elif choice == 3:
                    self.close()
                elif choice == 4:
                    text = input(">>>")
                    send_message(0x0E, '10.1.2.171', connection_socket, text.encode('utf-8'))

        except KeyboardInterrupt as e:
            print(e)
            self.close()
        except Exception as e:
            print(e)
            self.close()

        print('server is closed !')

    def receive(self):
        while self.is_running:
            try:
                data = self.connection_socket.recv(13)

                if not data:
                    self.close()
                    return

                header = Header.decode(data)
                print("protocol received code is {} sender is {} receiver is {} size is {}".format(header.CODE,
                                                                                                   header.SENDER,
                                                                                                   header.RECEIVER,
                                                                                                   header.SIZE))
                body_bytes = self.connection_socket.recv(header.SIZE)

                if header.CODE == HEARTBEAT:
                    print('heartbeat')
                elif header.CODE == START_FETCH:
                    data = json.loads(body_bytes)

                    if not data['is_success']:
                        print('패치 준비 실패')
                        continue

                    self.current_id = data['fetch_no']
                    threading.Thread(target=self.send_file).start()
                elif header.CODE == 0x0E:
                    print(body_bytes.decode('utf-8'))
            except socket.error as e:
                print(e)
                traceback.print_exc()

    def send_file(self):
        PIECE_SIZE = 1024 * 500
        # PIECE_SIZE = 500
        file_size = os.path.getsize(self.tmp_path)
        try:
            with open(self.tmp_path, 'rb') as file:
                total_send_size = 0

                while total_send_size != file_size:
                    current_send_size = PIECE_SIZE if total_send_size + PIECE_SIZE <= file_size else file_size - total_send_size
                    encoding_binary = base64.b64encode(file.read(current_send_size))
                    send_json_data = json.dumps({
                        "fetch_no": self.current_id,
                        "binary": encoding_binary.decode('utf-8'),
                        "is_final": total_send_size + PIECE_SIZE > file_size
                    })

                    send_message(SEND_FILE, '10.1.2.171', self.connection_socket, send_json_data.encode('utf-8'))

                    total_send_size += current_send_size
                    print(current_send_size, total_send_size, file_size)


        except Exception as e:
            print(e)
            traceback.print_exc()

    def close(self):
        self.is_running = False
        traceback.print_exc()
        print('server is closed')
        self.connection_socket.close()


client = TestClient()
client.start()
