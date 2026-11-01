import os

from common.node_main import run_node
from common.message_protocol import internal
from common.exchange_helper import bind_broadcast_queues
from .node import HistoricalReducer

OUTPUT_EXCHANGE = os.environ["OUTPUT_EXCHANGE"]
HIST_SHARD_COUNT = int(os.environ["HIST_SHARD_COUNT"])
CANDIDATE_SHARD_COUNT = int(os.environ["CANDIDATE_SHARD_COUNT"])


def create_output_exchange(incoming):
    exchange = incoming.create_exchange(OUTPUT_EXCHANGE, exchange_type="fanout")
    try:
        bind_broadcast_queues(exchange, "q5.candidate", CANDIDATE_SHARD_COUNT)
    except Exception:
        exchange.close()
        raise
    return exchange


def create_node(incoming, outgoing):
    return HistoricalReducer(incoming,
                             lambda message: outgoing.send(internal.serialize(message), routing_key=""),
                             HIST_SHARD_COUNT)


def main():
    if HIST_SHARD_COUNT < 1 or CANDIDATE_SHARD_COUNT < 1:
        raise ValueError("Shard counts must be positive")
    run_node(create_node, output_factory=create_output_exchange)


if __name__ == "__main__":
    main()
