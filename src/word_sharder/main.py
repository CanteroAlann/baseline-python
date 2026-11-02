import os
from common.node_main import run_node
from common.message_protocol import internal
from .node import WordSharderNode

OUTPUT_EXCHANGE = os.environ["OUTPUT_EXCHANGE"]

def create_output_exchange(incoming):
    return incoming.create_exchange(OUTPUT_EXCHANGE)

def create_node(incoming, outgoing, control):
    # Le pasamos el outgoing para que mande el resultado final al Gateway
    return WordSharderNode(incoming, outgoing, control)

def main():
    run_node(create_node, output_factory=create_output_exchange)

if __name__ == "__main__":
    main()