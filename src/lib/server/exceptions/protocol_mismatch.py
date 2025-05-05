class ProtocolMismatch(Exception):
    def __init__(self, message="Protocols are different and cannot intercommunicate"):
        self.message = message

    def __repr__(self):
        return f"ProtocolMismatch: {self.message})"
