from collections import Counter
from dataclasses import dataclass, field

from common.coordination import CoordinatorState
from common.enums import MsgType
from common.message import Message
from common.message_helper import MessageHelper, input_state
from common.message_protocol import internal


@dataclass
class SumState:
    counts: Counter[str] = field(default_factory=Counter)
    input: CoordinatorState = field(default_factory=input_state)


class Q4SumNode(MessageHelper):
    def __init__(self, incoming, outgoing, shard_id):
        super().__init__(incoming, None)
        self.outgoing = outgoing
        self.shard_id = shard_id
        self.sessions: dict[str, SumState] = {}

    def handle(self, message: Message):
        if not (message.is_word_count() or message.is_eof()):
            raise ValueError("Expected WORD_COUNT or EOF_RECORDS")
        state = self.sessions.setdefault(message.session_id, SumState())
        if message.is_word_count():
            state.counts.update(message.result)
            state.input.record_done(None)
        else:
            state.input.set_expected_count(message.expected_messages)

        if state.input.is_complete():
            top = sorted(state.counts.items(), key=lambda item: (-item[1], item[0]))[:20]
            result = Message(MsgType.TOP_LOCAL, message.session_id, shard_id=self.shard_id, result=top)
            self.outgoing.send(internal.serialize(result))
            del self.sessions[message.session_id]
