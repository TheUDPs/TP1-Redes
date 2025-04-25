class SocketShutdown(Exception):
    def __init__(self, message="Socket was shutdowned"):
        self.message = message
