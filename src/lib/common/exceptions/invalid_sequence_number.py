class InvalidSequenceNumber(Exception):
    def __init__(
        self, message="A packet with invalid sequence number was received", packet=None
    ):
        self.message = message
        self.packet = packet

    def __repr__(self):
        return f"InvalidSequenceNumber: {self.message})"
