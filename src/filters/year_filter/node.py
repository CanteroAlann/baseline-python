import logging
import os

from common.message_protocol import internal
from common.message import Message
from filters.filter_node import FilterNode

PRE2020_ROUTING_KEY = os.environ["PRE2020_ROUTING_KEY"]
POST2020_ROUTING_KEY = os.environ["POST2020_ROUTING_KEY"]


class YearFilterNode(FilterNode):
    def __init__(self, input_queue, output_exchange, control_queue):
        super().__init__(input_queue, output_exchange, None, control_queue)

    def process_article(self, message: Message) -> str | None:
        article = message.require_article()
        year = article.date_modified_year
        if year is None:
            logging.info(
                "YearFilterNode discarded undated article session=%s article_id=%s name=%r",
                message.session_id, message.article_id, article.name,
            )
            return None
        route = PRE2020_ROUTING_KEY if year <= 2020 else POST2020_ROUTING_KEY
        self.output_queue.send(internal.serialize(message), routing_key=route)
        logging.info(
            "YearFilterNode forwarded article session=%s article_id=%s name=%r year=%s routing_key=%s",
            message.session_id, message.article_id, article.name, year, route,
        )
        return route
