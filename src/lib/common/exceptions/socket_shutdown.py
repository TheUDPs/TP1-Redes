class SocketShutdown(Exception):
    def __init__(self, message="Socket was shutdowned"):
        self.message = message

    def __repr__(self):
        return f"SocketShutdown: {self.message})"
