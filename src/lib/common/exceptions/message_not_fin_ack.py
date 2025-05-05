class MessageIsNotFinAck(Exception):
    def __init__(self, message="The message is not an ACK and a FIN"):
        self.message = message

    def __repr__(self):
        return f"MessageIsNotFinAck: {self.message})"
