class UnexpectedFinMessage(Exception):
    def __init__(
            self,
            message="A packet with FIN was received when it was expected",
            packet=None):
        self.message = message
        self.packet = packet

    def __repr__(self):
        return f"UnexpectedFinMessage: {self.message})"
