import os

from common.node_main import run_node
from common.message_protocol import internal
from .node import HistoricalShard

SHARD_ID = int(os.environ["SHARD_ID"])


def create_node(incoming, outgoing):
    return HistoricalShard(incoming, lambda message: outgoing.send(internal.serialize(message)), SHARD_ID)


def main():
    run_node(create_node)


if __name__ == "__main__":
    main()
