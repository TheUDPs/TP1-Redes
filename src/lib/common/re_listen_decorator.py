import functools

from lib.common.constants import (
    MAX_RETRANSMISSION_ATTEMPTS,
)
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.invalid_sequence_number import InvalidSequenceNumber
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.message_not_fin import MessageIsNotFin
from lib.common.exceptions.message_not_fin_ack import MessageIsNotFinAck
from lib.common.exceptions.message_not_syn import MessageIsNotSyn
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage


def re_listen_if_failed(exceptions_to_let_through=None):
    def decorator(wrapped_function):
        @functools.wraps(wrapped_function)
        def wrapper(self, *args, **kwargs):
            _exceptions_to_let_through = kwargs.pop(
                "exceptions_to_let_through", exceptions_to_let_through
            )
            listening_attempts = 0
            result = None
            exception_got = None

            can_raise = [
                InvalidSequenceNumber,
                MessageIsNotAck,
                MessageIsNotFin,
                MessageIsNotFinAck,
                MessageIsNotSyn,
                UnexpectedFinMessage,
            ]
            want_to_catch = []

            if _exceptions_to_let_through is not None:
                for element in can_raise:
                    if element in _exceptions_to_let_through:
                        pass
                    else:
                        want_to_catch.append(element)
            else:
                want_to_catch = can_raise

            want_to_catch = tuple(want_to_catch)

            while listening_attempts < MAX_RETRANSMISSION_ATTEMPTS:
                try:
                    result = wrapped_function(self, *args, **kwargs)
                    break
                except want_to_catch as e:
                    exception_got = e
                    listening_attempts += 1
                    self.logger.debug(
                        f"Re-listening attempt attempt number {listening_attempts}. Due to error: {e.message}"
                    )
                except ConnectionLost as e:
                    exception_got = e
                    break

            if listening_attempts >= MAX_RETRANSMISSION_ATTEMPTS:
                self.logger.debug("Max package reception retrials reached")
                if exception_got is not None:
                    raise exception_got

            return result

        return wrapper

    return decorator
