class MessageIsNotAck(Exception):
    def __init__(self, message="The message is not an ACK", packet=None):
        self.message = message
        self.packet = packet

    def __repr__(self):
        return f"MessageIsNotAck: {self.message})"
