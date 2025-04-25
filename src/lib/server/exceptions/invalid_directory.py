class InvalidDirectory(Exception):
    def __init__(self, message="Invalid directory"):
        self.message = message
