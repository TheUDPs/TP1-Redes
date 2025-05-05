class MaxRetransmissionAttempts(Exception):
    def __init__(self, message="Max retransmission attempts reached"):
        self.message = message

    def __repr__(self):
        return f"Limit reached: {self.message})"
