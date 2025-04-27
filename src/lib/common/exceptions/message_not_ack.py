class MessageIsNotAck(Exception):
    def __init__(self, message="The message is not an ACK"):
        self.message = message

    def __repr__(self):
        return f"MessageIsNotAck: {self.message})"
