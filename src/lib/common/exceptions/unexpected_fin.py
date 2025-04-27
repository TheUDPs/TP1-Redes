class UnexpectedFinMessage(Exception):
    def __init__(self, message="A packet with FIN was received when it was expected"):
        self.message = message

    def __repr__(self):
        return f"UnexpectedFinMessage: {self.message})"
