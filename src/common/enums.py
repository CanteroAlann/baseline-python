from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    ERROR = 1


class MsgType(IntEnum):
    ARTICLE_RECORD = 1
    ARTICLE_RESULTS = 2
    ACK = 3
    EOF_RECORDS = 4
