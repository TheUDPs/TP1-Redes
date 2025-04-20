from typing import *
from threading import *

class Accepter:
    
    def __init__(self):
        self.host_direction = ('127.0.0.0', 8080)
        self.is_alive: bool = True

    def run(self):
        while self.is_alive:
            self.accept()           

    def accept(self):
        print(f"Connection accepted from {self.host_direction}")
        return 0 
