from common.enums import MsgType
import logging

from common.article import ExternalArticle
from common.message_protocol import internal


class FilterNode:
    def __init__(self, input_queue, output_queue, filter_function):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.filter_function = filter_function

    def process_message(self, body, ack, nack):
        message = internal.deserialize(body, ExternalArticle)
        if message["type"] == MsgType.ARTICLE_RECORD:
            article = message["article"]
            if not self.filter_function(article):
                logging.info(
                    "%s discarded article session=%s name=%r",
                    type(self).__name__, message["session_id"], article.name,
                )
                ack()
                return
            logging.info(
                "%s accepted article session=%s name=%r",
                type(self).__name__, message["session_id"], article.name,
            )
        elif message["type"] != MsgType.EOF_RECORDS:
            raise ValueError("Expected ARTICLE_RECORD or EOF_RECORDS")
        self.output_queue.send(body)
        logging.info(
            "%s published %s session=%s",
            type(self).__name__, message["type"].name, message["session_id"],
        )
        ack()

    def start(self):
        self.input_queue.start_consuming(self.process_message)
