from server.socket.server import Server


def init_module():
    """
    추가하고 싶은 기능의 모듈을 import

    :return:
    """
    import server.fetch
    import server.echo
    import server.chat


MainServer = Server()
init_module()
