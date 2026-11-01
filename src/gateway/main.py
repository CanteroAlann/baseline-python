import logging
import os
import signal
import socket
import sys
from dataclasses import dataclass

from common import middleware
from common.coordination import non_negative
from common.message import Message
from common.message_protocol import external as protocol
from common.enums import ExitCode, MsgType, QUERY_COUNT

from .message_handler import MessageHandler
from .client_socket import ClientSocket
from .server import GatewayServer


@dataclass
class QueryState:
    received_results: int = 0
    expected_results: int | None = None

    def is_complete(self):
        return self.expected_results is not None and self.received_results == self.expected_results


def handle_client_request(client_socket, output_queue, input_queue=None, query_count=QUERY_COUNT):
    handler = MessageHandler()
    owns_queue = input_queue is None
    if owns_queue:
        input_queue = output_queue.create_queue(
            f"{RESULT_EXCHANGE}.{handler.session_id}", exclusive=True,
        )
    try:
        input_queue.bind_exchange(RESULT_EXCHANGE, handler.session_id)
        logging.info(
            "Bound private results queue=%s session=%s",
            input_queue.queue_name, handler.session_id,
        )
        _handle_client_request(client_socket, output_queue, input_queue, handler, query_count)
    finally:
        if owns_queue:
            input_queue.close()


def _handle_client_request(client_socket, output_queue, input_queue, handler, query_count):
    logging.info("Started client session=%s", handler.session_id)
    while True:
        msg_type, article = protocol.recv_msg(client_socket)
        if msg_type == MsgType.ARTICLE_RECORD:
            output_queue.send(handler.serialize_data_message(article))
        elif msg_type == MsgType.EOF_RECORDS:
            output_queue.send(handler.serialize_eof_message())
            logging.info("Published input EOF session=%s", handler.session_id)
            break
        else:
            raise ValueError("Expected ARTICLE_RECORD or EOF_RECORDS")

    completed_queries = 0
    queries: dict[int, QueryState] = {}

    def consume_result(body, ack, nack):
        nonlocal completed_queries
        message = handler.deserialize_result_message(body)
        if message is None:
            ack()
            return
        query_id = message.require_query_id()
        state = queries.setdefault(query_id, QueryState())
        if message.is_query_result():
            state.received_results += 1
        else:
            state.expected_results = non_negative(message.expected_messages, "expected_messages")

        if state.expected_results is not None and state.received_results > state.expected_results:
            raise ValueError(f"Query {query_id} received more results than expected")

        if message.is_query_result():
            protocol.send_msg(client_socket, message.type, message)
            logging.info("Forwarded QUERY_RESULT query=%s session=%s", query_id, handler.session_id)

        if state.is_complete():
            eof = Message(MsgType.QUERY_EOF, query_id=query_id, expected_messages=state.expected_results)
            protocol.send_msg(client_socket, eof.type, eof)
            logging.info("Forwarded QUERY_EOF query=%s session=%s results=%s",
                         query_id, handler.session_id, state.received_results)
            completed_queries += 1
            if completed_queries == query_count:
                msg_type, _ = protocol.recv_msg(client_socket)
                if msg_type != MsgType.ACK:
                    raise ValueError("Expected final query results ACK")
                ack()
                input_queue.stop_consuming()
                return
        ack()

    try:
        input_queue.start_consuming(consume_result)
    finally:
        input_queue.stop_consuming()


SERVER_HOST = os.environ["SERVER_HOST"]
SERVER_PORT = int(os.environ["SERVER_PORT"])
SOCKET_TIMEOUT = 1800
CLIENT_CONNECTION_BACKLOG = 12
MAX_CLIENTS = 4
CHILD_SHUTDOWN_TIMEOUT = 5

MOM_HOST = os.environ["MOM_HOST"]
RESULT_EXCHANGE = os.environ["RESULT_EXCHANGE"]
OUTPUT_QUEUE = os.environ["OUTPUT_QUEUE"]


def handle_client_process(client_socket):
    logging.basicConfig(level=logging.INFO, format="%(processName)s[%(process)d] %(levelname)s %(message)s")
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(ExitCode.SUCCESS))
    signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(ExitCode.SUCCESS))
    output_queue = None
    with client_socket:
        try:
            output_queue = middleware.MessageMiddlewareQueueRabbitMQ(MOM_HOST, OUTPUT_QUEUE)
            connection = ClientSocket(client_socket, output_queue.process_events, SOCKET_TIMEOUT)
            handle_client_request(connection, output_queue)
        except (OSError, EOFError, ValueError, SyntaxError, TypeError, KeyError,
                middleware.MessageMiddlewareDisconnectedError,
                middleware.MessageMiddlewareMessageError) as exc:
            logging.warning("Client session ended: %s", exc)
            sys.exit(ExitCode.ERROR)
        finally:
            if output_queue is not None:
                output_queue.close()


def main():
    logging.basicConfig(level=logging.INFO)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        server_socket.listen(CLIENT_CONNECTION_BACKLOG)
        server = GatewayServer(server_socket, handle_client_process, max_clients=MAX_CLIENTS,
                               shutdown_timeout=CHILD_SHUTDOWN_TIMEOUT)
        signal.signal(signal.SIGTERM, server.stop)
        signal.signal(signal.SIGINT, server.stop)
        logging.info("Listening on %s:%d max_clients=%s", SERVER_HOST, SERVER_PORT, MAX_CLIENTS)
        server.run()


if __name__ == "__main__":
    main()
