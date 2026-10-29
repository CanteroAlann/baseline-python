import logging
import os
import signal
import socket
import sys

from common import middleware
from common.message_protocol import external as protocol
from common.enums import ExitCode, MsgType

from .message_handler import MessageHandler


def handle_client_request(client_socket, output_queue, input_queue=None):
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
        _process_client_request(client_socket, output_queue, input_queue, handler)
    finally:
        if owns_queue:
            input_queue.close()


"""
bloque de recepción de mensajes del cliente y publicación en la cola de salida
"""
def _process_client_request(client_socket, output_queue, input_queue, handler):
    logging.info("Started client session=%s", handler.session_id)
    while True:
        msg_type, article = protocol.recv_msg(client_socket)
        if msg_type == MsgType.ARTICLE_RECORD:
            output_queue.send(handler.serialize_data_message(article))
            logging.info(
                "Published article to year filter session=%s name=%r",
                handler.session_id, article.data["name"],
            )
        elif msg_type == MsgType.EOF_RECORDS:
            output_queue.send(handler.serialize_eof_message())
            logging.info("Published EOF to year filter session=%s", handler.session_id)
            break
        else:
            raise ValueError("Expected ARTICLE_RECORD or EOF_RECORDS")

    results = []

    def consume_result(body, ack, nack):
        message = handler.deserialize_result_message(body)
        if message is None:
            ack()
            return
        if message["type"] == MsgType.ARTICLE_RECORD:
            results.append((message["article"].url, message["article"].date_modified))
            logging.info(
                "Received matching article session=%s name=%r",
                handler.session_id, message["article"].name,
            )
            ack()
        elif message["type"] == MsgType.EOF_RECORDS:
            logging.info("Received EOF from filters session=%s", handler.session_id)
            protocol.send_msg(client_socket, MsgType.ARTICLE_RESULTS, results)
            logging.info(
                "Sent %d article results to client session=%s",
                len(results), handler.session_id,
            )
            msg_type, _ = protocol.recv_msg(client_socket)
            if msg_type != MsgType.ACK:
                raise ValueError("Expected result ACK")
            logging.info("Client acknowledged results session=%s", handler.session_id)
            ack()
            input_queue.stop_consuming()
        else:
            nack()
            raise ValueError("Unexpected result message")

    try:
        input_queue.start_consuming(consume_result)
    finally:
        input_queue.stop_consuming()


SERVER_HOST = os.environ["SERVER_HOST"]
SERVER_PORT = int(os.environ["SERVER_PORT"])
SOCKET_TIMEOUT = float(os.getenv("SOCKET_TIMEOUT", "120"))

MOM_HOST = os.environ["MOM_HOST"]
RESULT_EXCHANGE = os.environ["RESULT_EXCHANGE"]
OUTPUT_QUEUE = os.environ["OUTPUT_QUEUE"]

def main():
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(ExitCode.SUCCESS))
    output_queue = middleware.MessageMiddlewareQueueRabbitMQ(MOM_HOST, OUTPUT_QUEUE)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((SERVER_HOST, SERVER_PORT))
            server_socket.listen(1)
            logging.info("Listening on %s:%d", SERVER_HOST, SERVER_PORT)
            while True:
                client_socket, address = server_socket.accept()
                with client_socket:
                    client_socket.settimeout(SOCKET_TIMEOUT)
                    logging.info("Client connected: %s", address)
                    try:
                        handle_client_request(client_socket, output_queue)
                    except (OSError, EOFError, ValueError, SyntaxError, TypeError, KeyError) as exc:
                        logging.warning("Client session ended: %s", exc)
    finally:
        output_queue.close()


if __name__ == "__main__":
    main()
