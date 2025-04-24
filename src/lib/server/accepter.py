from threading import Thread
import socket
from typing import Tuple


class Accepter:
    def __init__(self, server_direction: tuple[str, int], protocol_id: str):
        self.host_direction: tuple[str, int] = server_direction
        self.is_alive: bool = True
        self.thread_context: Thread = Thread(target=self.run)
        self.welcoming_skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.welcoming_skt.bind(self.host_direction)
        self.clients = set()
        self.protocol_id: str = protocol_id
        self.logger = None

    def run(self):
        while self.is_alive:
            try:
                self.accept()
            except socket.timeout:
                continue
            except OSError as e:
                print(e)

    def accept(self):
        data, client_address = self.welcoming_skt.recvfrom(4096)

        if not client_address:
            return

        print(data.decode())

        self.clients.add(client_address)
        print(self.clients)

    def register_client(self, client_addr: Tuple[str, int], protocol_id: str):
        if client_addr in self.clients:
            return

        if protocol_id is not self.protocol_id:
            self.reject_conection(client_addr)
            return

        ## To-do Agregar la logica de aceptar al cliente

        return

    def reject_conection(self, client_addr: Tuple[str, int]):
        rejection_msj: str = "no"
        self.welcoming_skt.sendto(rejection_msj.encode(), client_addr)
        return 0

    def kill(self):
        self.is_alive = False

    def start(self):
        self.thread_context.start()

    def join(self):
        try:
            self.kill()
            self.welcoming_skt.shutdown(socket.SHUT_RDWR)
        except Exception as e:
            print(e)
        finally:
            self.thread_context.join()
