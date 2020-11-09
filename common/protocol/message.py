import struct
import json
import socket

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
RESULT_PREPARE_FETCH = 9
WAIT_FETCH = 10
REQUEST_CLIENT_STATE = 11
RESPONSE_CLIENT_STATE = 12
ALREADY_FETCH_ORDER = 13
TMP_CHAT = 14




class Header:
    def __init__(self,
                 size: int,
                 code: int,
                 sender: str, # todo: 4바이트의 정수값 사용하기 0x00|00|00|00(고민중)
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

    @property
    def json_body(self):
        return json.loads(self.BODY.decode('utf-8'))
