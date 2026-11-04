import os

from common.node_main import run_node
from .node import Q4JoinNode


OUTPUT_EXCHANGE = os.environ["OUTPUT_EXCHANGE"]
SHARD_COUNT = int(os.environ["SHARD_COUNT"])


def create_output_exchange(incoming):
    return incoming.create_exchange(OUTPUT_EXCHANGE)


def create_node(incoming, outgoing):
    return Q4JoinNode(incoming, outgoing, SHARD_COUNT)


def main():
    run_node(create_node, output_factory=create_output_exchange)


if __name__ == "__main__":
    main()