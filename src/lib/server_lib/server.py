from accepter import Accepter

CLOSING_KEY = "q"


class Server:
    def __init__(self):
        self.accepter: Accepter = Accepter(("127.0.0", 8080))
        self.filesyste = None

    def run(self):
        try:
            self.accepter.start()
            while True:
                user_input = input()
                if user_input.strip().lower() == CLOSING_KEY:
                    break
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
