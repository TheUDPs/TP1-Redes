from threading import Thread
import socket
import time


class Accepter:
    def __init__(self, server_direction: tuple[str, int]):
        self.host_direction: tuple[str, int] = server_direction
        self.is_alive: bool = True
        self.thread_context: Thread = Thread(target=self.run)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.host_direction)

    def run(self):
        try:
            while self.is_alive:
                data, client_address = self.socket.recvfrom(4096)
                time.sleep(1)
        except OSError as e:
            print("Se cerro el socket mientras esperaba")
            print(e)

    def accept(self):
        return 0

    def kill(self):
        self.is_alive = False

    def start(self):
        self.thread_context.start()

    def join(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.thread_context.join()
