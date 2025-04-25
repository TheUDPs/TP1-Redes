class InvalidSequenceNumber(Exception):
    def __init__(self, message="A packet with invalid sequence number was received"):
        self.message = message
