from dataclasses import dataclass, field
import logging

from common.coordination import CoordinatorState, non_negative
from common.enums import MsgType
from common.message import Message
from common.message_helper import MessageHelper, input_state


@dataclass
class HistoricalReducerState:
    input: CoordinatorState = field(default_factory=input_state)
    total: int = 0
    article_count: int = 0


class HistoricalReducer(MessageHelper):
    def __init__(self, incoming, emit, shard_count):
        super().__init__(incoming, emit)
        self.shard_count = shard_count
        self.sessions: dict[str, HistoricalReducerState] = {}

    def handle(self, message: Message):
        if not message.is_hist_partial() or message.shard_id not in range(self.shard_count):
            raise ValueError("Expected a historical partial from a configured shard")
        state = self.sessions.setdefault(message.session_id, HistoricalReducerState())
        state.input.set_expected_count(self.shard_count)
        state.total += non_negative(message.partial_sum, "partial_sum")
        state.article_count += non_negative(message.partial_count, "partial_count")
        state.input.record_done(None)
        if state.input.is_complete():
            logging.info("Q5 historical average ready session=%s total=%s articles=%s",
                         message.session_id, state.total, state.article_count)
            average = state.total / state.article_count if state.article_count else None
            self.emit(Message(MsgType.AVG_READY, message.session_id, average=average))
            logging.info("Q5 historical average session=%s average=%s articles=%s",
                         message.session_id, average, state.article_count)
            del self.sessions[message.session_id]
