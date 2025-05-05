class ClientAlreadyConnected(Exception):
    def __init__(self, message="Client is already connect"):
        self.message = message

    def __repr__(self):
        return f"ClientAlreadyConnected: {self.message})"
