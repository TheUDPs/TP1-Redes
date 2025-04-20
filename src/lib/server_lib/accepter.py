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
        self.clients = set()

    def run(self):
        while self.is_alive:
            try:
                data, client_address = self.socket.recvfrom(4096)
                print(data)
                if client_address in self.clients:
                    continue
                self.clients.add(client_address)
                time.sleep(1)
            except socket.timeout:
                print("Here")
                continue
            except OSError as e:
                print(e)

    def accept(self):
        return 0

    def kill(self):
        self.is_alive = False

    def start(self):
        self.thread_context.start()

    def join(self):
        try:
            self.kill()
            self.socket.shutdown(socket.SHUT_RDWR)
        except Exception as e:
            print(e)
        finally:
            self.thread_context.join()
