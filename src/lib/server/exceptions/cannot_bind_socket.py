class CannotBindSocket(Exception):
    def __init__(self, message="Cannot bind socket to port"):
        self.message = message

    def __repr__(self):
        return f"CannotBindSocket: {self.message})"
