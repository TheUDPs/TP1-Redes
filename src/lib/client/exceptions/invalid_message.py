class InvalidMessage(Exception):
    def __init__(self, message="Invalid message received"):
        self.message = message
