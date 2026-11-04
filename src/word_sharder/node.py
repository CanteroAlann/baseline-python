import logging
import os
import zlib

from common.article.clean_article import CleanArticle
from common.enums import MsgType
from common.message import Message
from common.message_helper import MessageHelper
from common.message_protocol import internal

class WordSharderNode(MessageHelper):
    def __init__(self, incoming, outgoing_exchange, control, shard_count):
        super().__init__(incoming, None)
        self.outgoing_exchange = outgoing_exchange
        self.control = control
        self.shard_count = shard_count
        self.input_eofs = {}
        self.batch_size = int(os.environ.get("BATCH_SIZE", 5))
        
    def process_message(self, body, ack, nack):
        # Forzamos a deserializar como CleanArticle
        self.handle(internal.deserialize(body, CleanArticle))
        ack()


    def handle(self, message: Message):
        session = message.session_id
        if message.is_article():
            article = message.require_article()
            words_by_shard = [[] for _ in range(self.shard_count)]
            # aplica el hash para cada palabra y la asigna a un shard
            logging.info(f"words_by_shard before: {len(words_by_shard)}")
            for word in article.abstract:
                shard_id = zlib.crc32(word.encode("utf-8")) % self.shard_count
                words_by_shard[shard_id].append(word)

            # debug
            # largos = {k: len(v) for k, v in enumerate(words_by_shard)}
            # logging.info(f"words_by_shard: {largos}")
            # logging.info(f"article.abstract: {len(article.abstract)}: {list(article.abstract)[:10]}")

            # por cada shard manda DONE al coordinador y WORD_COUNT al nodo de sum correspondiente
            for shard_id, words in enumerate(words_by_shard):
                route = f"q4.sum.{shard_id}"
                for i in range(0, len(words), self.batch_size):
                    chunk = words[i:i + self.batch_size]
                    
                    # envia el chunk en un solo mensaje
                    data = Message(MsgType.WORD_COUNT, session, article_id=message.article_id,
                                   shard_id=shard_id, result=chunk)
                    self.outgoing_exchange.send(internal.serialize(data), routing_key=route)
                    
                # por cada chunk enviado, avisa al coordinador cuantas palabras fueron
                done = Message(MsgType.DONE, session, output=route, produced_count=len(words))
                self.control.send(internal.serialize(done))

        elif message.is_eof():
            state = self.input_eofs.setdefault(session, {"count": 0, "expected": 0})
            state["count"] += 1
            state["expected"] += message.expected_messages or 0
            # ya que son pre2020 y post2020, esperamos 2 EOFs por sesión
            if state["count"] == 2:
                for shard_id in range(self.shard_count):
                    route = f"q4.sum.{shard_id}"
                    eof = Message(MsgType.INPUT_EOF, session, expected_messages=state["expected"],
                                  output=route)
                    self.control.send(internal.serialize(eof))
                del self.input_eofs[session]