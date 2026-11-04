from collections import defaultdict
import logging

from common.enums import MsgType
from common.message import Message
from common.message_helper import MessageHelper
from common.message_protocol import internal


class Q4SumNode(MessageHelper):
    def __init__(self, incoming, outgoing, shard_id):
        super().__init__(incoming, None)
        self.outgoing = outgoing
        self.shard_id = shard_id
        self.sessions = {}

    def process_message(self, body, ack, nack):
        self.handle(internal.deserialize(body))
        ack()

    def handle(self, message: Message):
        # el hash es deterministico, asi que cada palabra cae siempre en el mismo shard
        state = self.sessions.setdefault(message.session_id, {
            "counts": defaultdict(int), "received": 0, "expected": None,
        })
        # logging.info(f"Received message: {message.type} with word {message.word} and count {message.word_count}")
        if message.type == MsgType.WORD_COUNT:
            # va sumando las palabras por cada mensaje recibido
            state["counts"][message.word] += message.word_count
            state["received"] += 1
        elif message.is_eof():
            state["expected"] = message.expected_messages
        else:
            raise ValueError("Expected WORD_COUNT or EOF_RECORDS")


        if state["expected"] is not None and state["received"] == state["expected"]:
            # calcula un top local de palabras y manda el resultado
            top = sorted(state["counts"].items(), key=lambda item: (-item[1], item[0]))[:20]
            result = Message(MsgType.TOP_LOCAL, message.session_id, shard_id=self.shard_id, result=top)
            self.outgoing.send(internal.serialize(result), routing_key="q4.tops")
            del self.sessions[message.session_id]