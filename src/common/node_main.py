import logging
import os
import signal
import sys

from common import middleware
from common.enums import ExitCode

MOM_HOST = os.environ["MOM_HOST"]
INPUT_QUEUE = os.environ["INPUT_QUEUE"]
OUTPUT_QUEUE = os.environ["OUTPUT_QUEUE"]

def run_node(node_class):
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(ExitCode.SUCCESS))
    input_queue = middleware.MessageMiddlewareQueueRabbitMQ(MOM_HOST, INPUT_QUEUE)
    try:
        output_queue = input_queue.create_queue(OUTPUT_QUEUE)
        try:
            logging.info("%s waiting for articles", node_class.__name__)
            node_class(input_queue, output_queue).start()
        finally:
            output_queue.close()
    finally:
        input_queue.close()

