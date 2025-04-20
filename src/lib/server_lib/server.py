from typing import *
import threading
from accepter import Accepter

class Server:

    def __init__(self):
        self.accepter: Accepter = Accepter()
        self.filesyste = None 


    def run(self):
        try:
            self.accepter.start()
            print("Estoy aca esperando")

            while True: 
                user_input = input()
                print("Proceso input")
                if user_input.strip().lower() == "q":
                    print("Hago el break")
                    break
                print("No hice nada")
            self.accepter.kill()
            self.accepter.join()
            return 0
        except Exception as e:
            print(e)
            return -1 


if __name__ == "__main__":
    server: Server = Server()
    server.run()
    print("Server finished.")
    
