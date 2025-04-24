class UnexpectedMessage(Exception):
    def __init__(self, message="Received a message from an unexpected server"):
        self.message = message
