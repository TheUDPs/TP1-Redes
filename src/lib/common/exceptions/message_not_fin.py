class MessageIsNotFin(Exception):
    def __init__(self, message="The message is not a FIN"):
        self.message = message

    def __repr__(self):
        return f"MessageIsNotFin: {self.message})"
