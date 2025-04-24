import socket


class Client:
    def __init__(self, args, logger):
        self.args = args
        self.logger = logger
        self.some = None

    def run(self):
        skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        host = ("127.0.0.1", 8080)
        mensaje: bytes = "1".encode("utf-8")
        skt.sendto(mensaje, host)
        msj, server_address = skt.recvfrom(1048)
        if server_address != host:
            print(server_address)
            print("No es de quien esperaba el mensaje")

        else:
            print(msj.decode())
