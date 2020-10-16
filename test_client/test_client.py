import server
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


TEST_PACKET = 0x00
CLIENT_WELCOME = 0x01
FULL_CONN = 0x02
ECHO = 0x03
ORDER_FETCH = 0x04
RESULT_FETCH = 0x05
HEARTBEAT = 0x06
RESULT_SEND_FILE = 0x07
SEND_FILE = 0x08


# INSTALL = 0x05
# BYE = 0x06
# REQUEST_CLIENTS_STATE = 0x07
# RESPONSE_CLIENTS_STATE = 0x08
# ADMIN_WELCOME = 0x09
# HEARTBEAT = 0x0A

"""
import base64

with open("img.jpeg", "rb") as image_file:
    encoded_string = base64.b64encode(image_file.read())

    decoded_string = base64.b64decode(encoded_string)
    with open("test_img.jpeg", "w") as image_file2:
        image_file2.write(decoded_string)
로 보아 파일 이름 + 확장자가 필요하다        
"""

class Message:

    def __init__(self,
                 code: int,
                 sender: str,
                 receiver: str,
                 size: int,
                 data: bytes):
        self.code = code
        self.sender = sender
        self.receiver = receiver
        self.size = size
        self.data = data

    @classmethod
    def decode(cls, byte_data):
        header = struct.unpack('B4B4BL', byte_data[0:10])

        code = header[0]
        sender = '.'.join(header[1:5])
        receiver = '.'.join(header[5:9])
        size = header[9]

        return Message(code, sender, receiver, size, byte_data[10:10 + size])

    @classmethod
    def encode(cls, packet) -> bytes:
        get_ip = lambda ip: [int(piece) for piece in ip.split('.')]

        sender_ip_pieces = get_ip(packet.SENDER)
        receiver_ip_pieces = get_ip(packet.RECEIVER)

        print(sender_ip_pieces)
        print(receiver_ip_pieces)

        header = struct.pack('B4B4BL', packet.CODE, *sender_ip_pieces, *receiver_ip_pieces, packet.SIZE)
        data = header

        if packet.SIZE != 0:
            data += packet.data

        return data


HOST = '10.1.2.173'
PORT = 14444


class TestClient:
    def __init__(self):
        self.is_running = False
        self.client_socket = None
        self.thread = None
        self.my_id = None

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
                pass
            # while self.is_running:
            #     send_data = input(">>>").encode("utf-8")
            #     print()
            #     client_socket.send(Message.encode(
            #         Message(ECHO, server.gethostbyname(server.getfqdn()), '10.1.2.171', len(send_data), send_data)))
        except KeyboardInterrupt:
            self.close()

        print('server is closed')

    def receive(self):
        while self.is_running:
            data = self.client_socket.recv(1024)

            print(data)

            if not data:
                self.close()
                return

            message = Message.decode(data)
            print("protocol received code is {} sender is {} receiver is {} size is {}".format(message.code,
                                                                                              message.sender,
                                                                                              message.receiver,
                                                                                              message.size))

            if message.code == SEND_FILE:
                json_data = json.loads(message.data)
                print("fetch_id is {} checksum is {} ".format(json_data['fetch_id'], json_data['checksum']))


                file_name = json_data['file']['name']
                file_binary = None
                base64.decode(json_data['file']['binary'], file_binary)

                with open('C:\\Users\\devbong\\Desktop\\test_path\\' + file_name + "-" + datetime.datetime.now(), 'wb') as file:
                    file.write(file_binary)


                print('패치 파일을 받았습니다 전송할 결과를 선택하여 주세요')
                choice_number = int(input(">>>"))

                send_data = {
                    "end_date": datetime.datetime.now(),
                    "is_complete": True if choice_number == 0 else False
                    # 해당 코드에는 없지만 실제 클라이언트 엔진에서 패치 후 checksum 값과 비교하여 똑같으면 True로 결정
                }

                self.client_socket.sendall(Message.encode(
                    Message(RESULT_FETCH, server.gethostbyname(server.getfqdn()), '10.1.2.171', len(send_data),
                            send_data)
                ))

    def close(self):
        self.is_running = False
        self.client_socket.close()
        print('server is closed')
        exit(0)


client = TestClient()
client.start()
