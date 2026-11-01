import logging
import os
import signal
import sys

from common import middleware
from common.enums import ExitCode
from common.message_protocol import internal
from common.exchange_helper import publisher
from .node import CandidateShard

MOM_HOST = os.environ["MOM_HOST"]
INPUT_QUEUE = os.environ["INPUT_QUEUE"]
INPUT_EXCHANGE = os.environ["INPUT_EXCHANGE"]
INPUT_ROUTING_KEY = os.environ["INPUT_ROUTING_KEY"]
AVERAGE_EXCHANGE = os.environ["AVERAGE_EXCHANGE"]
RESULT_EXCHANGE = os.environ["RESULT_EXCHANGE"]
CONTROL_QUEUE = os.environ["CONTROL_QUEUE"]
SHARD_ID = int(os.environ["SHARD_ID"])


def main():
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(ExitCode.SUCCESS))
    incoming = middleware.MessageMiddlewareQueueRabbitMQ(MOM_HOST, INPUT_QUEUE)
    try:
        incoming.bind_exchange(INPUT_EXCHANGE, INPUT_ROUTING_KEY)
        incoming.bind_exchange(AVERAGE_EXCHANGE, "", exchange_type="fanout")
        control_queue = incoming.create_queue(CONTROL_QUEUE)
        try:
            results = incoming.create_exchange(RESULT_EXCHANGE)
            try:
                publish_result = publisher(results, mandatory=False)
                logging.info("CandidateShard waiting for shard=%s", SHARD_ID)
                CandidateShard(incoming, publish_result, SHARD_ID,
                               emit_done=lambda message: control_queue.send(internal.serialize(message))).start()
            finally:
                results.close()
        finally:
            control_queue.close()
    finally:
        incoming.close()


if __name__ == "__main__":
    main()
