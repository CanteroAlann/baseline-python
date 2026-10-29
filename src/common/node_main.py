import logging
import os
import signal
import sys

from common import middleware
from common.enums import ExitCode

MOM_HOST = os.environ["MOM_HOST"]
INPUT_QUEUE = os.environ["INPUT_QUEUE"]
OUTPUT_QUEUE = os.getenv("OUTPUT_QUEUE")
INPUT_EXCHANGE = os.getenv("INPUT_EXCHANGE")
INPUT_ROUTING_KEY = os.getenv("INPUT_ROUTING_KEY")


def run_node(node_class, output_factory=None):
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(ExitCode.SUCCESS))
    input_queue = middleware.MessageMiddlewareQueueRabbitMQ(
        MOM_HOST, INPUT_QUEUE,
    )
    try:
        if INPUT_EXCHANGE:
            input_queue.bind_exchange(INPUT_EXCHANGE, INPUT_ROUTING_KEY)
        # TODO: validar si OUTPUT_EXCHANGE existe como variable de entorno y está declarada
        output_queue = (
            output_factory(input_queue) if output_factory is not None
            else input_queue.create_queue(OUTPUT_QUEUE)
        )
        try:
            logging.info("%s waiting for articles", node_class.__name__)
            node_class(input_queue, output_queue).start()
        finally:
            output_queue.close()
    finally:
        input_queue.close()

