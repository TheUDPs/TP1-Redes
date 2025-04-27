class MissingServerAddress(Exception):
    def __init__(self, message="Server address not found"):
        self.message = message

    def __repr__(self):
        return f"MissingServerAddress: {self.message})"
