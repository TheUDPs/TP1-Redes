class ConnectionRefused(Exception):
    def __init__(self, message="Connection refused from server"):
        self.message = message
