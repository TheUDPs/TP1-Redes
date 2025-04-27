class MessageIsNotSyn(Exception):
    def __init__(self, message="The message is not a SYN"):
        self.message = message

    def __repr__(self):
        return f"MessageIsNotSyn: {self.message})"
