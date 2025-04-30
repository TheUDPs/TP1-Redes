import functools

from lib.common.constants import (
    MAX_RETRANSMISSION_ATTEMPTS,
)
from lib.common.exceptions.connection_lost import ConnectionLost
from lib.common.exceptions.invalid_sequence_number import InvalidSequenceNumber
from lib.common.exceptions.message_not_ack import MessageIsNotAck
from lib.common.exceptions.message_not_fin import MessageIsNotFin
from lib.common.exceptions.message_not_fin_ack import MessageIsNotFinAck
from lib.common.exceptions.message_not_fin_nor_ack import MessageNotFinNorAck
from lib.common.exceptions.message_not_syn import MessageIsNotSyn
from lib.common.exceptions.unexpected_fin import UnexpectedFinMessage


def configure_wanted_exceptions_to_catch(exceptions_to_let_through):
    want_to_catch_all = [
        InvalidSequenceNumber,
        MessageIsNotAck,
        MessageIsNotFin,
        MessageIsNotFinAck,
        MessageIsNotSyn,
        UnexpectedFinMessage,
        MessageNotFinNorAck,
        ConnectionLost,
    ]
    exceptions_subset = []

    if exceptions_to_let_through is not None:
        for element in want_to_catch_all:
            if element in exceptions_to_let_through:
                pass
            else:
                exceptions_subset.append(element)
    else:
        exceptions_subset = want_to_catch_all

    return tuple(exceptions_subset)


def re_listen_if_failed(exceptions_to_let_through=None):
    def decorator(wrapped_function):
        @functools.wraps(wrapped_function)
        def wrapper(self, *args, **kwargs):
            _exceptions_to_let_through = kwargs.pop(
                "exceptions_to_let_through", exceptions_to_let_through
            )
            want_to_catch = configure_wanted_exceptions_to_catch(
                _exceptions_to_let_through
            )

            listening_attempts = 0
            result = None
            exception_got = None

            while listening_attempts < MAX_RETRANSMISSION_ATTEMPTS:
                try:
                    result = wrapped_function(self, *args, **kwargs)
                    break
                except want_to_catch as e:
                    exception_got = e
                    listening_attempts += 1
                    self.logger.warn(
                        f"Re-listening attempt attempt number {listening_attempts}. Due to error: {e.message}"
                    )

            if listening_attempts >= MAX_RETRANSMISSION_ATTEMPTS:
                self.logger.warn("Max package reception retrials reached")
                if exception_got is not None:
                    raise exception_got

            return result

        return wrapper

    return decorator
