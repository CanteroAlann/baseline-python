import csv
import logging
import os
import signal
import socket
import sys
import time

from common.message_protocol import external as protocol


class Client:
    def __init__(self, timeout=120):
        self.server_socket = None
        self.timeout = timeout

    def connect(self, server_host, server_port):
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self.server_socket = socket.create_connection(
                    (server_host, server_port), timeout=min(5, self.timeout)
                )
                self.server_socket.settimeout(self.timeout)
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.2)

    def disconnect(self):
        if self.server_socket is not None:
            self.server_socket.close()
            self.server_socket = None

    def send_article_records(self, input_files):
        logging.info("Sending article records")
        csv.field_size_limit(sys.maxsize) # needed bc CSV rows are big
        for path in input_files:
            with open(path, newline="", encoding="utf-8-sig") as source:
                reader = csv.DictReader(source, strict=True)
                if not reader.fieldnames or "name" not in reader.fieldnames:
                    raise ValueError(f"{path}: missing name column")
                for article in reader:
                    if None in article or any(value is None for value in article.values()):
                        raise ValueError(f"{path}: malformed CSV record")
                    protocol.send_msg(self.server_socket, protocol.MsgType.ARTICLE_RECORD, article)
        protocol.send_msg(self.server_socket, protocol.MsgType.EOF_RECORDS)

    def recv_article_names(self, output=None):
        logging.info("Receiving article names")
        msg_type, names = protocol.recv_msg(self.server_socket)
        if msg_type != protocol.MsgType.ARTICLE_NAMES:
            raise ValueError("Expected ARTICLE_NAMES message")
        for name in names:
            print(name, file=output or sys.stdout, flush=True)
        protocol.send_msg(self.server_socket, protocol.MsgType.ACK)
        return names


def main():
    logging.basicConfig(level=logging.INFO)
    client = Client()
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    try:
        client.connect(os.environ["SERVER_HOST"], int(os.environ["SERVER_PORT"]))
        client.send_article_records([os.environ["INPUT_FILE"]])
        client.recv_article_names()
    except (OSError, EOFError, ValueError, KeyError, csv.Error) as exc:
        logging.error("Client failed: %s", exc)
        return 1
    finally:
        client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
