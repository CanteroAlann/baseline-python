from common.enums import MsgType
from common.message import Message
from common.message_protocol import internal


class Q3SharedWordsJoinNode:
    def __init__(self, incoming, outgoing, shard_count):
        self.input_queue = incoming
        self.outgoing = outgoing
        self.shard_count = shard_count
        self.sessions = {}

    def process_message(self, body, ack, nack):
        message = internal.deserialize(body)
        if message.type != MsgType.TOP_LOCAL or not isinstance(message.result, list):
            raise ValueError("Expected a local query 3 result")
        state = self.sessions.setdefault(message.session_id, {})
        state[message.shard_id] = message.result
        if len(state) == self.shard_count:
            shared = sorted({word for words in state.values() for word in words})
            result = Message(
                MsgType.QUERY_RESULT,
                query_id=3,
                result=shared,
            )
            self.outgoing.send(internal.serialize(result), routing_key=message.session_id)
            eof = Message(MsgType.QUERY_EOF, query_id=3, expected_messages=1)
            self.outgoing.send(internal.serialize(eof), routing_key=message.session_id)
            del self.sessions[message.session_id]
        ack()

    def start(self):
        self.input_queue.start_consuming(self.process_message)
