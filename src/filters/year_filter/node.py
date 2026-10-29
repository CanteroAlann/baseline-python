import logging
import os

from common.article import ExternalArticle
from common.enums import MsgType
from common.message_protocol import internal

PRE2020_ROUTING_KEY = os.environ["PRE2020_ROUTING_KEY"]
POST2020_ROUTING_KEY = os.environ["POST2020_ROUTING_KEY"]


class YearFilterNode:
    def __init__(self, input_queue, output_exchange):
        self.input_queue = input_queue
        self.output_exchange = output_exchange

    def process_message(self, body, ack, nack):
        message = internal.deserialize(body, ExternalArticle)
        logging.info("New message received: %s, session=%s", message["type"].name, message["session_id"])
        if message["type"] == MsgType.ARTICLE_RECORD:
            article = message["article"]
            year = article.date_modified_year
            if year is None:
                logging.info(
                    "YearFilterNode discarded undated article session=%s name=%r",
                    message["session_id"], article.name,
                )
                ack()
                return
            routing_keys = (PRE2020_ROUTING_KEY if year <= 2020 else POST2020_ROUTING_KEY,)
        elif message["type"] == MsgType.EOF_RECORDS:
            routing_keys = (PRE2020_ROUTING_KEY, POST2020_ROUTING_KEY)
        else:
            raise ValueError("Expected ARTICLE_RECORD or EOF_RECORDS")
        for routing_key in routing_keys:
            self.output_exchange.send(body, routing_key=routing_key)
            logging.info(
                "YearFilterNode published %s session=%s routing_key=%s",
                message["type"].name, message["session_id"], routing_key,
            )
        ack()

    def start(self):
        self.input_queue.start_consuming(self.process_message)
