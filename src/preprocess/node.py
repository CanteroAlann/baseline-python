import logging

from common.article import ExternalArticle
from common.enums import MsgType
from common.message import Message
from common.message_protocol import internal
from .preprocess import Preprocessor


class PreprocessNode:
    def __init__(self, input_queue, output_exchange, control_queue):
        self.input_queue = input_queue
        self.output_exchange = output_exchange
        self.control_queue = control_queue
        self.preprocessor = Preprocessor()

    def process_message(self, body, ack, nack, routing_key):
        message = internal.deserialize(body, ExternalArticle)
        if message.is_article():
            article = message.require_article()
            if not isinstance(article, ExternalArticle):
                raise ValueError("Preprocessing requires an external article")
            message.article = self.preprocessor.process(article)
            self.output_exchange.send(internal.serialize(message), routing_key=routing_key)
            control = Message(MsgType.DONE, message.session_id, output=routing_key)
            logging.info("Preprocessed article session=%s article_id=%s routing_key=%s",
                         message.session_id, message.article_id, routing_key)
        elif message.is_eof():
            control = Message(MsgType.INPUT_EOF, message.session_id,
                              expected_messages=message.expected_messages, output=routing_key)
        else:
            raise ValueError("Expected ARTICLE_RECORD or EOF_RECORDS")
        self.control_queue.send(internal.serialize(control))
        ack()

    def start(self):
        self.input_queue.start_consuming(self.process_message, include_routing_key=True)
