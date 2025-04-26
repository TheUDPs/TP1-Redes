class InvalidMessage(Exception):
    def __init__(self, message="Invalid message received"):
        self.message = message

    def __repr__(self):
        return f"InvalidMessage: {self.message})"
