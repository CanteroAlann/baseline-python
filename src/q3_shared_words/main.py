import os

from common.node_main import run_node
from .node import Q3SharedWordsShard

OUTPUT_EXCHANGE = os.environ["OUTPUT_EXCHANGE"]
SHARD_ID = int(os.environ["SHARD_ID"])


def create_output_exchange(incoming):
    return incoming.create_exchange(OUTPUT_EXCHANGE)


def create_node(incoming, outgoing, control):
    return Q3SharedWordsShard(incoming, outgoing, control, SHARD_ID)


def main():
    run_node(create_node, output_factory=create_output_exchange)


if __name__ == "__main__":
    main()
