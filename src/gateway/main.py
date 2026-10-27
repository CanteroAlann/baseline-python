import logging
import os
import signal
import socket
import sys

from common.message_protocol import external as protocol


def handle_client_request(client_socket):
    names = []
    while True:
        msg_type, article = protocol.recv_msg(client_socket)
        if msg_type == protocol.MsgType.ARTICLE_RECORD:
            names.append(article["name"])
        elif msg_type == protocol.MsgType.EOF_RECORDS:
            break
        else:
            raise ValueError("Expected ARTICLE_RECORD or EOF_RECORDS")

    logging.info("Received all %d articles; sending names", len(names))
    protocol.send_msg(client_socket, protocol.MsgType.ARTICLE_NAMES, names)
    msg_type, _ = protocol.recv_msg(client_socket)
    if msg_type != protocol.MsgType.ACK:
        raise ValueError("Expected result ACK")


def main():
    logging.basicConfig(level=logging.INFO)
    host = os.environ["SERVER_HOST"]
    port = int(os.environ["SERVER_PORT"])
    timeout = float(os.getenv("SOCKET_TIMEOUT", "120"))
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(1)
        logging.info("Listening on %s:%d", host, port)
        while True:
            client_socket, address = server_socket.accept()
            with client_socket:
                client_socket.settimeout(timeout)
                logging.info("Client connected: %s", address)
                try:
                    handle_client_request(client_socket)
                except (OSError, EOFError, ValueError) as exc:
                    logging.warning("Client session ended: %s", exc)


if __name__ == "__main__":
    main()
