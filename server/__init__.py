from server.socket.server import Server


def init_module():
    import server.fetch


MainServer = Server()
init_module()
