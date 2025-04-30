class MessageNotFinNorAck(Exception):
    def __init__(self, message="The message is not an ACK nor a FIN"):
        self.message = message

    def __repr__(self):
        return f"MessageNotFinNorAck: {self.message})"
