import server
import threading
import json
import struct

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


HOST = '192.168.91.1'
PORT = 14454


class TestClient:
    def __init__(self):
        self.is_running = False
        self.client_socket = None
        self.thread = None

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
            while self.is_running:
                send_data = input(">>>").encode("utf-8")
                print()
                self.client_socket.send(Message.encode(Message(ECHO, server.gethostbyname(server.getfqdn()), '10.1.2.171', len(send_data), send_data)))
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

            if message.code == ECHO:
                print("protocol : " + message.data.decode("utf-8"))
            elif message.code == HEARTBEAT:
                print("heartBeat")

    def close(self):
        self.is_running = False
        self.client_socket.close()
        print('server is closed')
        exit(0)


client = TestClient()
client.start()

