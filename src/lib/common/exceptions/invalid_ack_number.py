class InvalidAckNumber(Exception):
    def __init__(self, message="A packet with invalid ACK number was received"):
        self.message = message

    def __repr__(self):
        return f"InvalidAckNumber: {self.message})"
