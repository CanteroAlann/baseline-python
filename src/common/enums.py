from enum import IntEnum
import os


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
    WORD_COUNT = 9
    HIST_PARTIAL = 10
    AVG_READY = 11
    TOP_LOCAL = 12


QUERY_IDS = (1, 2, 3, 4, 5)
# Keep this aligned with the services in generate_compose.py
# Override con ENABLED_QUERY_IDS para tests
ENABLED_QUERY_IDS = tuple(
    int(q) for q in os.environ.get("ENABLED_QUERY_IDS", "1,2,3,4,5").split(",") if q.strip()
)


QUERY_COUNT = len(ENABLED_QUERY_IDS)
