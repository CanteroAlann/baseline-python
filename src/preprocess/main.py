import os

from common.node_main import INPUT_EXCHANGE, run_node
from .node import PreprocessNode

OUTPUT_EXCHANGE = os.environ["OUTPUT_EXCHANGE"]


def create_output_exchange(incoming):
    if INPUT_EXCHANGE == OUTPUT_EXCHANGE:
        raise ValueError("Preprocessing input and output exchanges must be different")
    return incoming.create_exchange(OUTPUT_EXCHANGE)


def main():
    run_node(PreprocessNode, output_factory=create_output_exchange)


if __name__ == "__main__":
    main()
