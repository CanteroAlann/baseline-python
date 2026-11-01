from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    ERROR = 1


class MsgType(IntEnum):
    ARTICLE_RECORD = 1
    ARTICLE_RESULTS = 2
    ACK = 3
    EOF_RECORDS = 4
    INPUT_EOF = 5
    DONE = 6
    QUERY_RESULT = 7
    QUERY_EOF = 8


QUERY_IDS = (1, 2, 3, 4, 5)
QUERY_COUNT = 2  # Increase as the other queries are implemented.
