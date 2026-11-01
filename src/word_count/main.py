import os

from common.node_main import run_node
from common.exchange_helper import bind_shards
from .node import WordCountNode

OUTPUT_EXCHANGE = os.environ["OUTPUT_EXCHANGE"]
BRANCH = os.environ["BRANCH"]
SHARD_COUNT = int(os.environ["SHARD_COUNT"])


def create_output_exchange(incoming):
    exchange = incoming.create_exchange(OUTPUT_EXCHANGE)
    try:
        bind_shards(exchange, f"q5.{BRANCH}", SHARD_COUNT)
    except Exception:
        exchange.close()
        raise
    return exchange


def create_node(incoming, outgoing, control):
    return WordCountNode(incoming, outgoing, control, branch=BRANCH, shard_count=SHARD_COUNT)


def main():
    run_node(create_node, output_factory=create_output_exchange)


if __name__ == "__main__":
    main()
