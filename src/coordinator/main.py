import json
import os
import signal
import sys

from common import middleware
from common.enums import ExitCode
from common.logging_config import configure_worker_logging
from .node import CoordinatorNode

MOM_HOST = os.environ["MOM_HOST"]
INPUT_QUEUE = os.environ["INPUT_QUEUE"]
OUTPUT_EXCHANGE = os.environ["OUTPUT_EXCHANGE"]
OUTPUT_ROUTING_KEYS = tuple(filter(None, os.environ.get("OUTPUT_ROUTING_KEYS", "").split(",")))
OUTPUT_BINDINGS = json.loads(os.environ.get("OUTPUT_BINDINGS", "{}"))
QUERY_ID = int(os.environ["QUERY_ID"]) if os.environ.get("QUERY_ID") else None
INDEPENDENT_ROUTES = os.environ.get("INDEPENDENT_ROUTES", "false").lower() == "true"
EXPECTED_INPUTS = int(os.environ["EXPECTED_INPUTS"]) if os.environ.get("EXPECTED_INPUTS") else None
INPUT_ROUTES = tuple(filter(None, os.environ.get("INPUT_ROUTES", "").split(",")))


def main():
    configure_worker_logging()
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(ExitCode.SUCCESS))
    incoming = middleware.MessageMiddlewareQueueRabbitMQ(MOM_HOST, INPUT_QUEUE)
    try:
        outgoing = incoming.create_exchange(OUTPUT_EXCHANGE)
        try:
            for queue, route in OUTPUT_BINDINGS.items():
                outgoing.bind_queue(queue, route)
            CoordinatorNode(incoming, outgoing, OUTPUT_ROUTING_KEYS, query_id=QUERY_ID,
                            independent_routes=INDEPENDENT_ROUTES, expected_inputs=EXPECTED_INPUTS,
                            input_routes=INPUT_ROUTES).start()
        finally:
            outgoing.close()
    finally:
        incoming.close()


if __name__ == "__main__":
    main()
