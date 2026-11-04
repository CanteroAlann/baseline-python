import os

from common.node_main import run_node
from .node import Q4SumNode


SHARD_ID = int(os.environ["SHARD_ID"])


def create_node(incoming, outgoing):
    return Q4SumNode(incoming, outgoing, SHARD_ID)


def main():
    run_node(create_node)


if __name__ == "__main__":
    main()
