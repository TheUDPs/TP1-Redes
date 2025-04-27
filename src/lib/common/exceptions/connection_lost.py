class ConnectionLost(Exception):
    def __init__(self, message="Connection was lost"):
        self.message = message

    def __repr__(self):
        return f"ConnectionLost: {self.message})"
