class BadFlagsForHandshake(Exception):
    def __init__(
        self, message="Flags in the packet for the handshake are in an unexpected state"
    ):
        self.message = message

    def __repr__(self):
        return f"BadFlagsForHandshake: {self.message})"
