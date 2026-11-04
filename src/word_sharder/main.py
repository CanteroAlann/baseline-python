import os
from common.node_main import run_node
from common.exchange_helper import bind_shards
from .node import WordSharderNode

OUTPUT_EXCHANGE = os.environ["OUTPUT_EXCHANGE"]
SHARD_COUNT = int(os.environ["Q4_SHARD_COUNT"])

def create_output_exchange(incoming):
    exchange = incoming.create_exchange(OUTPUT_EXCHANGE)
    try:
        bind_shards(exchange, "q4.sum", SHARD_COUNT)
    except Exception:
        exchange.close()
        raise
    return exchange

def create_node(incoming, outgoing, control):
    return WordSharderNode(incoming, outgoing, control, SHARD_COUNT)

def main():
    run_node(create_node, output_factory=create_output_exchange)

if __name__ == "__main__":
    main()
