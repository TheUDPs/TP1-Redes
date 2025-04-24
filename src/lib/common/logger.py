from datetime import datetime


class Logger:
    DEBUG_LOG_LEVEL = 4  # debug + info + errors + warns
    INFO_LOG_LEVEL = 3  # info + errors + warns
    WARN_LEVEL = 2
    QUIET_LOG_LEVEL = 1  # errors
    ERROR_LEVEL = 0

    PRINTABLE_LEVELS = {
        DEBUG_LOG_LEVEL: "DEBUG",
        INFO_LOG_LEVEL: "INFO",
        WARN_LEVEL: "WARN",
        ERROR_LEVEL: "ERROR",
    }

    """
    level can be: DEBUG_LOG_LEVEL, INFO_LOG_LEVEL or QUIET_LOG_LEVEL
    """

    def __init__(self, level=INFO_LOG_LEVEL):
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
            print(f"[{timestamp}] [{self.PRINTABLE_LEVELS[msg_level]}] {message}")

    def debug(self, message):
        self._log(self.DEBUG_LOG_LEVEL, message)

    def info(self, message):
        self._log(self.INFO_LOG_LEVEL, message)

    def error(self, message):
        self._log(self.ERROR_LEVEL, message)

    def warn(self, message):
        self._log(self.WARN_LEVEL, message)
