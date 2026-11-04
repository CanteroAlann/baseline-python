import zlib

from common.article import CleanArticle
from common.enums import MsgType
from common.message import Message
from common.message_helper import MessageHelper
from common.message_protocol import internal

BATCH_SIZE = 5


class WordSharderNode(MessageHelper):
    def __init__(self, incoming, outgoing_exchange, control, shard_count):
        super().__init__(incoming, None)
        if shard_count < 1:
            raise ValueError("Shard count must be positive")
        self.outgoing_exchange = outgoing_exchange
        self.control = control
        self.shard_count = shard_count

    def process_message(self, body, ack, nack, routing_key=None):
        self.handle(internal.deserialize(body, CleanArticle), routing_key)
        ack()

    def handle(self, message: Message, routing_key=None):
        session = message.session_id
        if message.is_article():
            article = message.require_article()
            if not isinstance(article, CleanArticle):
                raise ValueError("Word sharding requires a cleaned article")
            words_by_shard = [[] for _ in range(self.shard_count)]
            for word in article.abstract:
                shard_id = zlib.crc32(word.encode("utf-8")) % self.shard_count
                words_by_shard[shard_id].append(word)

            for shard_id, words in enumerate(words_by_shard):
                route = f"q4.sum.{shard_id}"
                produced = 0
                for index in range(0, len(words), BATCH_SIZE):
                    chunk = words[index:index + BATCH_SIZE]
                    data = Message(MsgType.WORD_COUNT, session, article_id=message.article_id,
                                   shard_id=shard_id, result=chunk)
                    self.outgoing_exchange.send(internal.serialize(data), routing_key=route)
                    produced += 1
                done = Message(MsgType.DONE, session, output=route, produced_count=produced)
                self.control.send(internal.serialize(done))
        elif message.is_eof():
            if routing_key is None:
                raise ValueError("Expected the input routing key on EOF_RECORDS")
            eof = Message(MsgType.INPUT_EOF, session, expected_messages=message.expected_messages,
                          input_route=routing_key)
            self.control.send(internal.serialize(eof))
        else:
            raise ValueError("Expected ARTICLE_RECORD or EOF_RECORDS")

    def start(self):
        self.input_queue.start_consuming(self.process_message, include_routing_key=True)
