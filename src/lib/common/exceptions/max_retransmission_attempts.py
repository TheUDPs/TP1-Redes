class MaxRetransmissionAttempts(Exception):
    def __init__(
            self,
            message="Max retransmission attempts for a packet reached."):
        self.message = message

    def __repr__(self):
        return f"MaxRetransmissionAttempts: {self.message})"
