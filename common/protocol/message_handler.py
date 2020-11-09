from abc import ABCMeta, abstractmethod

from common.protocol.message import Message, Header

receivers = []
"""
:type list(MessageReceiver)

수신된 메시지 처리 헨들러 객체를 저장하고 있는 리스트
Server 에서 메시지 수신시 send_message() 호출하고 
해당 리스트를 탐색해 적절함 헨들러 객체를 찾아 처리하기 때문에 반드시 헨들러 객체는 이 리스트에 저장되어 있어야함

"""


class MessageReceiver(metaclass=ABCMeta):
    """
    수신된 메세지를 처리하기 위한 클래스를 만들기 위해선 반드시 해당 클래스를 상속해야함
    """

    def __init__(self):
        receivers.append(self)

    @abstractmethod
    def receive(self,
                message: Message,
                client):
        """
        직접적으로 메시지(Message)를 받는 메소드
        
        :param message: 
        :param client: 수신한 클라이언트 통신 소켓
        :return: 
        """
        pass

    @abstractmethod
    def is_message_take(self,
                        message: Message) -> bool:
        """
        처리할 수 있는 메시지인가 확인하는 메소드

        :param message:
        :return:
        """
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
            # 등록된 것중 맞는 receiver 찾아 수신처리
            receiver.receive(message, client)


def make_message(code: int,
                 sender_ip: str,
                 receiver_ip: str,
                 body=None):
    header = Header(0 if body is None else len(body), code, sender_ip, receiver_ip)
    data = Header.encode(header)

    if body:
        data += body  # todo: 미리 크기를 알 수 있으므로 리스트를 사용하지 말고, 배열을 이용하여 byte 데이터를 만드는 방식으로 취할것

    # print('send data')
    # print("protocol received code is {} sender is {} receiver is {} size is {}".format(header.CODE,
    #                                                                                    header.SENDER,
    #                                                                                    header.RECEIVER,
    #                                                                                    header.SIZE))

    return data


def send_message(code: int,
                 sender_ip: str,
                 receiver,
                 body: bytes = None):
    receiver.send(make_message(code, sender_ip, receiver.ip, body))


def multi_send_message(code: int,
                       sender_ip: str,
                       clients,
                       body: bytes = None):
    for client in clients:
        send_message(code, sender_ip, client, body)
