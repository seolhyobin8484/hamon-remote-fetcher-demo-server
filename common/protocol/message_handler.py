import server
from abc import ABCMeta, abstractmethod

from common.protocol.message import Message, Header

receivers = []

SERVER_ID = 0x00


class MessageReceiver(metaclass=ABCMeta):

    def __init__(self):
        receivers.append(self)

    @abstractmethod
    def receive(self,
                message: Message,
                client):
        pass

    @abstractmethod
    def is_message_take(self,
                        message: Message) -> bool:
        pass


def receive_message(client,
                    message: Message):

    print('receive data')
    print("protocol received code is {} sender is {} receiver is {} size is {}".format(message.HEADER.CODE,
                                                                                      message.HEADER.SENDER,
                                                                                      message.HEADER.RECEIVER,
                                                                                      message.HEADER.SIZE))
    for receiver in receivers:
        if receiver.is_message_take(message):
            receiver.receive(message, client)


def send_message(code: int,
                 client,
                 body=None):

    header = Header(code, server.gethostbyname(server.getfqdn()), client.ip, 0 if body is None else len(body))
    data = Header.encode(header)

    if body:
        data += body

    client.send(data)

