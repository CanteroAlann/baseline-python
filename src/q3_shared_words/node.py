import logging
from dataclasses import dataclass, field

from common.coordination import CoordinatorState
from common.enums import MsgType
from common.message import Message
from common.message_helper import MessageHelper, input_state
from common.message_protocol import internal

RESULT_BATCH_SIZE = 100


@dataclass
class SharedWordsState:
    english: set[str] = field(default_factory=set)
    french: set[str] = field(default_factory=set)
    input: CoordinatorState = field(default_factory=input_state)


class Q3SharedWordsShard(MessageHelper):
    def __init__(self, incoming, outgoing, control_queue, shard_id):
        super().__init__(incoming, None)
        self.outgoing = outgoing
        self.control_queue = control_queue
        self.shard_id = shard_id
        self.sessions: dict[str, SharedWordsState] = {}

    def handle(self, message: Message):
        if not (message.is_word_count() or message.is_eof()):
            raise ValueError("Expected WORD_COUNT or EOF_RECORDS")
        state = self.sessions.setdefault(message.session_id, SharedWordsState())
        if message.is_word_count():
            if not isinstance(message.result, list):
                raise ValueError("Expected a list of words in each chunk")
            language = (message.language or "").lower()
            if language == "en":
                state.english.update(message.result)
            elif language == "fr":
                state.french.update(message.result)
            # Every chunk counts toward EOF, including other languages.
            state.input.record_done(None)
        else:
            state.input.set_expected_count(message.expected_messages)

        if state.input.is_complete():
            shared = sorted(state.english & state.french)
            produced = 0
            for index in range(0, len(shared), RESULT_BATCH_SIZE):
                result = Message(MsgType.QUERY_RESULT, query_id=3,
                                 result=shared[index:index + RESULT_BATCH_SIZE])
                self.outgoing.send(internal.serialize(result), routing_key=message.session_id, mandatory=False)
                produced += 1
            done = Message(MsgType.DONE, message.session_id, output="output",
                           shard_id=self.shard_id, produced_count=produced)
            self.control_queue.send(internal.serialize(done))
            logging.info("Q3 shard completed session=%s shard=%s chunks=%s shared_words=%s result_batches=%s",
                         message.session_id, self.shard_id, state.input.processed, len(shared), produced)
            del self.sessions[message.session_id]
