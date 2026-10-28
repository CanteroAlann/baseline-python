from common.enums import MsgType
import logging

from common.article import ExternalArticle
from common.message_protocol import internal
from .preprocess import Preprocessor


class PreprocessNode:
    def __init__(self, input_queue, output_queue):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.preprocessor = Preprocessor()

    def process_message(self, body, ack, nack):
        message = internal.deserialize(body, ExternalArticle)
        if message["type"] == MsgType.ARTICLE_RECORD:
            logging.info(
                "Received article session=%s name=%r",
                message["session_id"], message["article"].data["name"],
            )
            message["article"] = self.preprocessor.process(message["article"])
            logging.info(
                "Processed article session=%s name=%r abstract_word_count=%d unique_words=%d",
                message["session_id"], message["article"].name,
                message["article"].abstract_word_count, len(message["article"].abstract),
            )
        elif message["type"] != MsgType.EOF_RECORDS:
            raise ValueError("Expected ARTICLE_RECORD or EOF_RECORDS")
        self.output_queue.send(internal.serialize(message))
        logging.info(
            "Published %s to filters session=%s",
            message["type"].name, message["session_id"],
        )
        ack()

    def start(self):
        self.input_queue.start_consuming(self.process_message)