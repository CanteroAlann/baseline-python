from collections import deque
from dataclasses import dataclass, field

from common.coordination import CoordinatorState, non_negative
from common.enums import MsgType
from common.message import Message
from common.message_helper import MessageHelper, input_state


@dataclass
class CandidateState:
    input: CoordinatorState = field(default_factory=input_state)
    pending: deque[tuple[int, str, int]] = field(default_factory=deque)
    average: float | None = None
    average_ready: bool = False
    produced_results: int = 0

    def is_complete(self):
        return self.input.is_complete() and self.average_ready and not self.pending


class CandidateShard(MessageHelper):
    def __init__(self, incoming, emit_result, shard_id, *, emit_done):
        super().__init__(incoming, emit_result)
        self.emit_done = emit_done
        self.shard_id = shard_id
        self.sessions: dict[str, CandidateState] = {}

    def _compare(self, session_id, state, article_id, url, word_count):
        if state.average is not None and word_count > state.average:
            result = Message(MsgType.QUERY_RESULT, query_id=5, article_id=article_id,
                             result={"url": url, "word_count": word_count})
            self.emit(result, session_id)
            state.produced_results += 1

    def handle(self, message: Message):
        state = self.sessions.setdefault(message.session_id, CandidateState())
        if message.is_word_count():
            if message.shard_id != self.shard_id:
                raise ValueError("Candidate data delivered to the wrong shard")
            count = non_negative(message.word_count, "word_count")
            article_id = non_negative(message.article_id, "article_id")
            url = message.url
            if not isinstance(url, str):
                raise ValueError("Candidate must include a URL")
            if state.average_ready:
                self._compare(message.session_id, state, article_id, url, count)
            else:
                state.pending.append((article_id, url, count))
            state.input.record_done(None)
        elif message.is_eof():
            state.input.set_expected_count(message.expected_messages)
        elif message.is_avg_ready():
            state.average = message.average
            state.average_ready = True
            while state.pending:
                self._compare(message.session_id, state, *state.pending[0])
                state.pending.popleft()
        else:
            raise ValueError("Expected WORD_COUNT, EOF or AVG_READY")
        if state.is_complete():
            self.emit_done(Message(MsgType.DONE, message.session_id, shard_id=self.shard_id,
                                   output="output", produced_count=state.produced_results))
            del self.sessions[message.session_id]
