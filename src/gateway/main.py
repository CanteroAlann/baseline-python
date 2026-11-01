import logging
import os
import signal
import socket
import sys
import base64

from common import middleware
from common.message_protocol import external as protocol
from common.enums import ExitCode, MsgType, QUERY_COUNT

from .message_handler import MessageHandler
from .client_socket import ClientSocket
from .server import GatewayServer


"""
bloque de recepción de mensajes del cliente y publicación en la cola de salida
"""
def _process_client_request(client_socket, output_queue, input_queue, handler):
    logging.info("Started client session=%s", handler.session_id)
    while True:
        msg_type, article = protocol.recv_msg(client_socket)
        # logging.info(f"ASD msg_type={msg_type}")
        if msg_type == MsgType.ARTICLE_RECORD:
            output_queue.send(handler.serialize_data_message(article))
        elif msg_type == MsgType.EOF_RECORDS:
            output_queue.send(handler.serialize_eof_message())
            logging.info("Published input EOF session=%s", handler.session_id)
            break
        else:
            raise ValueError("Expected ARTICLE_RECORD or EOF_RECORDS")

        
def handle_client_request(client_socket, output_queue, input_queue=None, query_count=QUERY_COUNT):
    completed_queries = 0

    handler = MessageHandler()
    owns_queue = input_queue is None
    if owns_queue:
        input_queue = output_queue.create_queue(
            f"{RESULT_EXCHANGE}.{handler.session_id}", exclusive=True,
        )
    def consume_result(body, ack, nack):
        nonlocal completed_queries
        message = handler.deserialize_result_message(body)
        if message is None:
            ack()
            return
        if not (message.is_query_result() or message.is_query_eof()):
            raise ValueError("Expected QUERY_RESULT or QUERY_EOF")
        query_id = message.require_query_id()
        protocol.send_msg(client_socket, message.type, message)
        logging.info("Forwarded %s query=%s session=%s", message.type.name, query_id, handler.session_id)
        if message.is_query_eof():
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
        input_queue.bind_exchange(RESULT_EXCHANGE, handler.session_id)
        logging.info(
            "Bound private results queue=%s session=%s",
            input_queue.queue_name, handler.session_id,
        )
        _process_client_request(client_socket, output_queue, input_queue, handler)
        input_queue.start_consuming(consume_result)
    finally:
        input_queue.stop_consuming()
        if owns_queue:
            input_queue.close()


SERVER_HOST = os.environ["SERVER_HOST"]
SERVER_PORT = int(os.environ["SERVER_PORT"])
SOCKET_TIMEOUT = 120
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
