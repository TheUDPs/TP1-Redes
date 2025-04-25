class BadOperation(Exception):
    def __init__(self, message="Invalid operation"):
        self.message = message
