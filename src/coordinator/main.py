import json
import logging
import os
import signal
import sys

from common import middleware
from common.enums import ExitCode
from .node import CoordinatorNode

MOM_HOST = os.environ["MOM_HOST"]
INPUT_QUEUE = os.environ["INPUT_QUEUE"]
OUTPUT_EXCHANGE = os.environ["OUTPUT_EXCHANGE"]
OUTPUT_ROUTING_KEYS = tuple(filter(None, os.environ.get("OUTPUT_ROUTING_KEYS", "").split(",")))
OUTPUT_BINDINGS = json.loads(os.environ.get("OUTPUT_BINDINGS", "{}"))
QUERY_ID = int(os.environ["QUERY_ID"]) if os.environ.get("QUERY_ID") else None


def main():
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(ExitCode.SUCCESS))
    incoming = middleware.MessageMiddlewareQueueRabbitMQ(MOM_HOST, INPUT_QUEUE)
    try:
        outgoing = incoming.create_exchange(OUTPUT_EXCHANGE)
        try:
            for queue, route in OUTPUT_BINDINGS.items():
                outgoing.bind_queue(queue, route)
            CoordinatorNode(incoming, outgoing, OUTPUT_ROUTING_KEYS, query_id=QUERY_ID).start()
        finally:
            outgoing.close()
    finally:
        incoming.close()


if __name__ == "__main__":
    main()
