import os
import zlib

from common.article import CleanArticle
from common.coordination import Coordinator
from common.enums import MsgType
from common.message import Message
from common.message_protocol import internal


class Q3SharedWordsNode:
    """Fan out preprocessed articles and coordinate one EOF per vocabulary shard."""

    def __init__(self, incoming, outgoing, shard_count):
        if shard_count < 1:
            raise ValueError("shard_count must be positive")
        self.input_queue = incoming
        self.outgoing = outgoing
        self.shard_count = shard_count
        self.eof_state = {}
        self.expected_input_routes = int(os.environ.get("INPUT_ROUTE_COUNT", "2"))
        if self.expected_input_routes < 1:
            raise ValueError("INPUT_ROUTE_COUNT must be positive")
        routes = tuple(f"q3.shared.{shard_id}" for shard_id in range(shard_count))
        self.coordinator = Coordinator(self.publish_eof, routes, independent_routes=True)

    def publish_eof(self, message, routing_key):
        self.outgoing.send(internal.serialize(message), routing_key=routing_key)

    def process_message(self, body, ack, nack):
        message = internal.deserialize(body, CleanArticle)
        if message.is_article():
            article = message.require_article()
            language = (article.in_language or "").lower()
            words = article.abstract if language in {"en", "fr"} else set()
            by_shard = [[] for _ in range(self.shard_count)]
            for word in words:
                shard_id = zlib.crc32(word.encode("utf-8")) % self.shard_count
                by_shard[shard_id].append(word)

            for shard_id, shard_words in enumerate(by_shard):
                route = f"q3.shared.{shard_id}"
                data = Message(
                    MsgType.WORD_COUNT,
                    message.session_id,
                    article_id=message.article_id,
                    shard_id=shard_id,
                    result={"language": language, "words": shard_words},
                )
                self.outgoing.send(internal.serialize(data), routing_key=route)
                self.coordinator.handle(Message(
                    MsgType.DONE, message.session_id, output=route, produced_count=1,
                ))
        elif message.is_eof():
            state = self.eof_state.setdefault(
                message.session_id, {"count": 0, "expected": 0},
            )
            state["count"] += 1
            state["expected"] += message.expected_messages or 0
            if state["count"] == self.expected_input_routes:
                for shard_id in range(self.shard_count):
                    route = f"q3.shared.{shard_id}"
                    self.coordinator.handle(Message(
                        MsgType.INPUT_EOF,
                        message.session_id,
                        output=route,
                        expected_messages=state["expected"],
                    ))
                del self.eof_state[message.session_id]
        else:
            raise ValueError("Expected ARTICLE_RECORD or EOF_RECORDS")
        ack()

    def start(self):
        self.input_queue.start_consuming(self.process_message)


class Q3SharedWordsShard:
    def __init__(self, incoming, outgoing, shard_id):
        self.input_queue = incoming
        self.outgoing = outgoing
        self.shard_id = shard_id
        self.sessions = {}

    def process_message(self, body, ack, nack):
        message = internal.deserialize(body)
        state = self.sessions.setdefault(message.session_id, {
            "english": set(), "french": set(), "received": 0, "expected": None,
        })
        if message.is_word_count():
            if not isinstance(message.result, dict):
                raise ValueError("Expected a query 3 word payload")
            language = message.result.get("language")
            words = message.result.get("words")
            if not isinstance(words, list):
                raise ValueError("Expected a list of query 3 words")
            state["received"] += 1
            if language in {"en", "fr"}:
                state["english" if language == "en" else "french"].update(words)
            elif words:
                raise ValueError("Non-English/French payload cannot contain words")
        elif message.is_eof():
            state["expected"] = message.expected_messages
        else:
            raise ValueError("Expected WORD_COUNT or EOF_RECORDS")

        if state["expected"] is not None and state["received"] == state["expected"]:
            shared = sorted(state["english"] & state["french"])
            result = Message(
                MsgType.TOP_LOCAL,
                message.session_id,
                shard_id=self.shard_id,
                result=shared,
            )
            self.outgoing.send(internal.serialize(result), routing_key="q3.tops")
            del self.sessions[message.session_id]
        ack()

    def start(self):
        self.input_queue.start_consuming(self.process_message)
