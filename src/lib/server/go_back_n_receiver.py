from lib.common.file_handler import FileHandler
from lib.common.logger import Logger
from lib.common.sequence_number import SequenceNumber
from lib.server.protocol_gbn import ServerProtocolGbn


class GoBackNReceiver:
    def __init__(
        self,
        logger: Logger,
        protocol: ServerProtocolGbn,
        file_handler: FileHandler,
        sequence_number: SequenceNumber,
        ack_number: SequenceNumber,
    ) -> None:
        # self.windows_size: int = WINDOWS_SIZE
        self.base: int = 0
        self.logger: Logger = logger
        self.protocol: ServerProtocolGbn = protocol
        self.sqn_number: SequenceNumber = sequence_number
        self.ack_number: SequenceNumber = ack_number
        self.next_seq_num: int = 0
        self.file_handler: FileHandler = file_handler

    def receive_file(self, file) -> None:
        self.logger.debug("Beginning file reception in GBN manner")
