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
