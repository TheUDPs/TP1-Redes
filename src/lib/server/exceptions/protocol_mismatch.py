class ProtocolMismatch(Exception):
    def __init__(self, message="Protocols are different and cannot intercommunicate"):
        self.message = message
