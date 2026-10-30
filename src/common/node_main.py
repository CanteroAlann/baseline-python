import logging
import os
import signal
import sys

from common import middleware
from common.enums import ExitCode

MOM_HOST = os.environ["MOM_HOST"]
INPUT_QUEUE = os.environ["INPUT_QUEUE"]
OUTPUT_QUEUE = os.environ.get("OUTPUT_QUEUE")
INPUT_EXCHANGE = os.environ.get("INPUT_EXCHANGE")
INPUT_ROUTING_KEY = os.environ.get("INPUT_ROUTING_KEY")
COORDINATOR_QUEUE = os.environ.get("COORDINATOR_QUEUE")


def run_node(node_class, output_factory=None):
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(ExitCode.SUCCESS))
    input_queue = middleware.MessageMiddlewareQueueRabbitMQ(
        MOM_HOST, INPUT_QUEUE,
    )
    try:
        if INPUT_EXCHANGE:
            input_queue.bind_exchange(INPUT_EXCHANGE, INPUT_ROUTING_KEY)
        output_queue = (
            output_factory(input_queue) if output_factory is not None
            else input_queue.create_queue(OUTPUT_QUEUE)
        )
        try:
            control = input_queue.create_queue(COORDINATOR_QUEUE) if COORDINATOR_QUEUE else None
            try:
                logging.info("%s waiting for articles", node_class.__name__)
                args = (input_queue, output_queue, control) if control else (input_queue, output_queue)
                node_class(*args).start()
            finally:
                if control:
                    control.close()
        finally:
            output_queue.close()
    finally:
        input_queue.close()

