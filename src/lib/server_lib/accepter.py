import threading
from typing import *
from threading import *
import time 

class Accepter:
    
    def __init__(self, server_direction: tuple[str, int]):
        self.host_direction = ('127.0.0.0', 8080)
        self.is_alive: bool = True
        self.thread_context: Thread = threading.Thread(target=self.run) 
        

    def run(self):
        while self.is_alive:
            time.sleep(1)
            new_client: int = self.accept()           
        

    def accept(self):
        return 0 

    def kill(self): 
        self.is_alive = False

    def start(self):
        self.thread_context.start()

    def join(self):
        self.thread_context.join()
