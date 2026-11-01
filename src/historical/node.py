from dataclasses import dataclass, field

from common.coordination import CoordinatorState, non_negative
from common.enums import MsgType
from common.message import Message
from common.message_helper import MessageHelper, input_state


@dataclass
class HistoricalState:
    input: CoordinatorState = field(default_factory=input_state)
    total: int = 0


class HistoricalShard(MessageHelper):
    def __init__(self, incoming, emit, shard_id):
        super().__init__(incoming, emit)
        self.shard_id = shard_id
        self.sessions: dict[str, HistoricalState] = {}

    def handle(self, message: Message):
        state = self.sessions.setdefault(message.session_id, HistoricalState())
        if message.is_word_count():
            if message.shard_id != self.shard_id:
                raise ValueError("Historical data delivered to the wrong shard")
            state.total += non_negative(message.word_count, "word_count")
            state.input.record_done(None)
        elif message.is_eof():
            state.input.set_expected_count(message.expected_messages)
        else:
            raise ValueError("Expected WORD_COUNT or EOF")
        if state.input.is_complete():
            self.emit(Message(MsgType.HIST_PARTIAL, message.session_id, shard_id=self.shard_id,
                              partial_sum=state.total, partial_count=state.input.processed))
            del self.sessions[message.session_id]
