from accepter import Accepter

CLOSING_KEY = "q"


class Server:
    def __init__(self, args, logger):
        self.args = args
        self.args = logger
        self.accepter: Accepter = Accepter(("127.0.0.1", 8080), "2")
        self.filesyste = None

    def run(self):
        try:
            self.accepter.start()
            while True:
                user_input: str = input()
                if user_input.strip().lower() == CLOSING_KEY:
                    break
            self.accepter.join()
            return 0
        except Exception as e:
            print(e)
            return -1
