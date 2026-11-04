from collections import defaultdict

from common.enums import MsgType
from common.message import Message
from common.message_protocol import internal


class Q4JoinNode:
    def __init__(self, incoming, outgoing, shard_count):
        self.input_queue = incoming
        self.outgoing = outgoing
        self.shard_count = shard_count
        self.sessions = {}

    def process_message(self, body, ack, nack):
        message = internal.deserialize(body)
        # guarda los mensajes de cada shard por sesión
        state = self.sessions.setdefault(message.session_id, {})
        state[message.shard_id] = message.result

        # una vez recibido el resultado de todos los shards, calcula el top global
        if len(state) == self.shard_count:
            counts = defaultdict(int)
            for local_top in state.values():
                for word, count in local_top:
                    counts[word] += count
            top = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:20]
            result = Message(MsgType.QUERY_RESULT, session_id=message.session_id,
                             query_id=4, result=top)
            self.outgoing.send(internal.serialize(result), routing_key=message.session_id)
            eof = Message(MsgType.QUERY_EOF, query_id=4, expected_messages=1)
            self.outgoing.send(internal.serialize(eof), routing_key=message.session_id)
            del self.sessions[message.session_id]
        ack()

    def start(self):
        self.input_queue.start_consuming(self.process_message)