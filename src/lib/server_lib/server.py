from typing import *

class Server:

    def __init__(self) -> None:
        self.acceptador = None
        self.filesyste = None 


    def run(self):
        try:
            # self.acceptador.run()
            # self.filesystem.start()
            while input() != 'q':
                print("Server is running...")
                pass
            # self.acceptador.finalize()
            # self.filesyste.finalize()
            return 0
        except Exception as e:
            print(e)
            return -1 



if __name__ == "__main__":
    server: Server = Server()
    server.run()
    print("Server finished.")
    
