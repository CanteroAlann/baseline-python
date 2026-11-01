import os

from common.node_main import run_node
from .node import YearFilterNode, PRE2020_ROUTING_KEY

OUTPUT_EXCHANGE = os.environ["OUTPUT_EXCHANGE"]
PRE2020_QUEUE = os.environ["PRE2020_QUEUE"]
PREPROCESS_QUEUE = os.environ["PREPROCESS_QUEUE"]
PREPROCESS_ROUTING_KEY = os.environ["PREPROCESS_ROUTING_KEY"]
BIOGRAPHY_QUEUE = os.environ["BIOGRAPHY_QUEUE"]


def create_output_exchange(input_queue):
    exchange = input_queue.create_exchange(OUTPUT_EXCHANGE)
    try:
        exchange.bind_queue(PRE2020_QUEUE, PRE2020_ROUTING_KEY)
        exchange.bind_queue(PREPROCESS_QUEUE, PREPROCESS_ROUTING_KEY)
        exchange.bind_queue(BIOGRAPHY_QUEUE, PRE2020_ROUTING_KEY)
    except Exception:
        exchange.close()
        raise
    return exchange


def main():
    run_node(YearFilterNode, output_factory=create_output_exchange)


if __name__ == "__main__":
    main()
