class RetransmissionNeeded(Exception):
    def __init__(self, message="Retransmission is needed"):
        self.message = message

    def __repr__(self):
        return f"RetransmissionNeeded: {self.message})"
