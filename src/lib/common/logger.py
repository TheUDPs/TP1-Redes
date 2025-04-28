from datetime import datetime
from logging import Logger


def get_logger(verbose, quiet) -> Logger:
    if verbose:
        return Logger(Logger.DEBUG_LOG_LEVEL)
    elif quiet:
        return Logger(Logger.QUIET_LOG_LEVEL)
    else:
        return Logger(Logger.INFO_LOG_LEVEL)


class Colors:
    RED = "\033[1;31m"
    GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[1;34m"
    RESET = "\033[0m"


class Logger:
    DEBUG_LOG_LEVEL = 4  # debug + info + errors + warns
    WARN_LEVEL = 3.5
    INFO_LOG_LEVEL = 3  # info + errors + warns
    QUIET_LOG_LEVEL = 1  # errors
    ERROR_LEVEL = 0

    PRINTABLE_LEVELS = {
        DEBUG_LOG_LEVEL: Colors.BLUE + "DEBUG" + Colors.RESET,
        INFO_LOG_LEVEL: Colors.GREEN + "INFO" + Colors.RESET,
        WARN_LEVEL: Colors.YELLOW + "WARN" + Colors.RESET,
        ERROR_LEVEL: Colors.RED + "ERROR" + Colors.RESET,
    }

    """
    level can be: DEBUG_LOG_LEVEL, INFO_LOG_LEVEL or QUIET_LOG_LEVEL
    """

    def __init__(self, level=INFO_LOG_LEVEL):
        self.prefix: str = ""

        if level <= self.QUIET_LOG_LEVEL:
            self.current_level = self.QUIET_LOG_LEVEL
        elif level == self.INFO_LOG_LEVEL:
            self.current_level = self.INFO_LOG_LEVEL
        elif level == self.DEBUG_LOG_LEVEL:
            self.current_level = self.DEBUG_LOG_LEVEL
        else:
            self.current_level = self.INFO_LOG_LEVEL

    def _log(self, msg_level, message):
        if self.current_level >= msg_level:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(
                f"[{timestamp}] [{self.PRINTABLE_LEVELS[msg_level]}]{self.prefix} {message}",
                flush=True,
            )

    def _force_log(self, msg_level, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(
            f"[{timestamp}] [{self.PRINTABLE_LEVELS[msg_level]}]{self.prefix} {message}",
            flush=True,
        )

    def debug(self, message):
        self._log(self.DEBUG_LOG_LEVEL, message)

    def info(self, message):
        self._log(self.INFO_LOG_LEVEL, message)

    def force_info(self, message):
        self._force_log(self.INFO_LOG_LEVEL, message)

    def error(self, message):
        self._log(self.ERROR_LEVEL, message)

    def warn(self, message):
        self._log(self.WARN_LEVEL, message)

    def set_prefix(self, prefix: str):
        self.prefix = " " + prefix.strip()

    def clone(self, keep_prefix=False) -> Logger:
        logger = Logger()
        logger.current_level = self.current_level

        if keep_prefix:
            logger.prefix = self.prefix

        return logger
