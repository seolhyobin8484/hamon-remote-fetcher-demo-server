import socket
import threading
import json
import struct
import base64
import datetime

# code - 1byte
# sender - 4byte
# receiver - 4byte
# size - 4byte
# total : 13byte

# data is always json-format
import time
import traceback

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
    header = Header(code, '10.1.2.171', ip, 0 if body is None else len(body))
    data = Header.encode(header)

    if body:
        data += body

    conn.sendall(data)


HOST = '10.1.2.171'
PORT = 14494


class TestClient:
    def __init__(self):
        self.is_running = False
        self.client_socket = None
        self.thread = None
        self.my_id = None

        self.is_receiving = False
        self.current_fetch = None
        self.file = None

    def start(self):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))

        print('서버 연결 성공')

        self.is_running = True
        self.client_socket = client_socket

        thread = threading.Thread(target=self.receive)
        thread.start()

        self.thread = thread

        try:
            while True:
                pass
            # while self.is_running:
            #     send_data = input(">>>").encode("utf-8")
            #     print()
            #     client_socket.send(Message.encode(
            #         Message(ECHO, socket.gethostbyname(socket.getfqdn()), '10.1.2.171', len(send_data), send_data)))
        except KeyboardInterrupt:
            self.close()

        print('socket is closed')

    def receive(self):
        try:
            while self.is_running:
                header_bytes = self.client_socket.recv(16)

                if not header_bytes:
                    self.close()
                    return

                header = Header.decode(header_bytes)
                body_bytes = self.client_socket.recv(header.SIZE)

                while len(body_bytes) != header.SIZE:
                    body_bytes += self.client_socket.recv(header.SIZE - len(body_bytes))

                message = Message(header, body_bytes)

                print("message received code is {} sender is {} receiver is {} size is {}".format(message.HEADER.CODE,
                                                                                                  message.HEADER.SENDER,
                                                                                                  message.HEADER.RECEIVER,
                                                                                                  message.HEADER.SIZE))

                if message.HEADER.CODE == ORDER_FETCH:
                    json_data = json.loads(message.BODY)
                    self.current_fetch = json_data
                    self.is_receiving = True

                    self.file = open('C:/Users/devbong/Desktop/test_path/{}.{}'.format(json_data['file']['name'] + '-2',
                                                                                       json_data['file']['ext']), 'wb')

                elif message.HEADER.CODE == SEND_FILE:

                    json_data = json.loads(message.BODY.decode('utf-8'))
                    file_binary = base64.b64decode(json_data['binary'])

                    self.file.write(file_binary)

                    if json_data.get('is_final', False):
                        print('패치 파일을 받았습니다 전송할 결과를 선택하여 주세요')
                        print('성공 : 0, 실패 : 1')
                        choice_number = int(input(">>>"))

                        send_data = {
                            "fetch_no": self.current_fetch['fetch_no'],
                            "end_date": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "is_complete": True if choice_number == 0 else False
                            # 해당 코드에는 없지만 실제 클라이언트 엔진에서 패치 후 checksum 값과 비교하여 똑같으면 True로 결정
                        }

                        self.file.close()
                        send_message(RESULT_FETCH, '10.1.2.171', self.client_socket,
                                     json.dumps(send_data).encode('utf-8'))
        except Exception as e:
            print(e)
            traceback.print_exc()


    def close(self):
        self.is_running = False
        self.client_socket.close()
        print('socket is closed')
        exit(0)


client = TestClient()
client.start()