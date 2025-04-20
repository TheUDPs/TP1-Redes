from threading import Thread
import time


class Accepter:
    def __init__(self, server_direction: tuple[str, int]):
        self.host_direction: tuple[str, int] = server_direction
        self.is_alive: bool = True
        self.thread_context: Thread = Thread(target=self.run)

    def run(self):
        while self.is_alive:
            time.sleep(1)

    def accept(self):
        return 0

    def kill(self):
        self.is_alive = False

    def start(self):
        self.thread_context.start()

    def join(self):
        self.thread_context.join()
