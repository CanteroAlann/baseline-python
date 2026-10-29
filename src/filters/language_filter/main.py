import os

from common.node_main import run_node
from .node import LanguageFilterNode

OUTPUT_EXCHANGE = os.environ["OUTPUT_EXCHANGE"]


def create_output_exchange(input_queue):
    return input_queue.create_exchange(OUTPUT_EXCHANGE)


def main():
    run_node(LanguageFilterNode, output_factory=create_output_exchange)


if __name__ == "__main__":
    main()
