from common.enums import MsgType
from csv import DictReader, field_size_limit, writer
import logging
import socket
import sys
import time

from common.article import ExternalArticle
from common.message_protocol import external as protocol

DEFAULT_TIMEOUT = 120
CSV_ENCODING = "utf-8-sig"

CLIENT_SLEEP_TIME = 0.2  # seconds


class Client:
    def __init__(self, timeout=DEFAULT_TIMEOUT):
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
                time.sleep(CLIENT_SLEEP_TIME)

    def disconnect(self):
        if self.server_socket is not None:
            self.server_socket.close()
            self.server_socket = None

    def send_article_records(self, file_path):
        logging.info("Sending article records")
        field_size_limit(sys.maxsize) # needed bc CSV rows are big
        
        with open(file_path, newline="", encoding=CSV_ENCODING) as source:
            reader = DictReader(source, strict=True)
            
            if not reader.fieldnames:
                raise ValueError(f"{file_path}: missing field names in CSV header")
            
            for article in reader:
                if None in article or any(value is None for value in article.values()):
                    raise ValueError(f"{file_path}: malformed CSV record")
                
                protocol.send_msg(self.server_socket, MsgType.ARTICLE_RECORD, ExternalArticle(article))
        
        protocol.send_msg(self.server_socket, MsgType.EOF_RECORDS)

    def recv_article_results(self):
        logging.info("Receiving article results")
        msg_type, results = protocol.recv_msg(self.server_socket)
        
        if msg_type != MsgType.ARTICLE_RESULTS:
            raise ValueError("Expected ARTICLE_RESULTS message")
        
        out = sys.stdout
        writer(out).writerows(results)
        out.flush()

        protocol.send_msg(self.server_socket, MsgType.ACK)
        return results
