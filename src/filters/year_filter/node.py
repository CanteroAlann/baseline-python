import os

from common.message_protocol import internal
from common.message import Message
from filters.filter_node import FilterNode

PRE2020_ROUTING_KEY = os.environ["PRE2020_ROUTING_KEY"]
POST2020_ROUTING_KEY = os.environ["POST2020_ROUTING_KEY"]


class YearFilterNode(FilterNode):
    def __init__(self, input_queue, output_exchange, coordinator_queue):
        super().__init__(input_queue, output_exchange, None, coordinator_queue)

    def process_article(self, message: Message) -> str | None:
        year = message.require_article().date_modified_year
        if year is None:
            return None
        route = PRE2020_ROUTING_KEY if year <= 2020 else POST2020_ROUTING_KEY
        self.output_queue.send(internal.serialize(message), routing_key=route)
        return route
