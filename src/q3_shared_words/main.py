import os

from common.node_main import run_node
from common.exchange_helper import bind_shards
from .node import Q3SharedWordsNode

OUTPUT_EXCHANGE = os.environ["OUTPUT_EXCHANGE"]
SHARD_COUNT = int(os.environ["SHARD_COUNT"])


def create_output_exchange(incoming):
    exchange = incoming.create_exchange(OUTPUT_EXCHANGE)
    try:
        bind_shards(exchange, "q3.shared", SHARD_COUNT)
    except Exception:
        exchange.close()
        raise
    return exchange


def create_node(incoming, outgoing):
    return Q3SharedWordsNode(incoming, outgoing, SHARD_COUNT)


if __name__ == "__main__":
    run_node(create_node, output_factory=create_output_exchange)
