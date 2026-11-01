from common.node_main import run_node
from .node import BiographyFilterNode


def main():
    run_node(BiographyFilterNode)

# el bindeo de las queues ya se hace en el node_main, leyendo directo del docker-compose

if __name__ == "__main__":
    main()