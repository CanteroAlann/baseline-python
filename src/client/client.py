from common.enums import MsgType, QUERY_COUNT
from csv import DictReader, field_size_limit
import logging
import socket
import sys
import time

from common.article import ExternalArticle
from common.message import Message
from common.message_protocol import external as protocol

DEFAULT_TIMEOUT = 1800
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

    def recv_query_results(self, query_count=QUERY_COUNT):
        results = {}
        completed_queries = 0
        while completed_queries < query_count:
            _, message = protocol.recv_msg(self.server_socket)
            if not isinstance(message, Message):
                raise ValueError("Expected a query result or EOF")
            query_id = message.require_query_id()
            records = results.setdefault(query_id, [])
            if message.is_query_result():
                records.append(message)
                logging.info("Received Query %s partial result: %s", query_id, message.result)
            elif message.is_query_eof():
                completed_queries += 1
                logging.info("Query %s finished", query_id)
            else:
                raise ValueError("Expected QUERY_RESULT or QUERY_EOF")

        protocol.send_msg(self.server_socket, MsgType.ACK)
        final_results = {}
        for query_id, records in results.items():
            records.sort(key=lambda record: record.article_id or 0)
            final_results[query_id] = [record.result for record in records]
            logging.info("Query %s final results (%d): %s", query_id,
                         len(records), final_results[query_id])
        return final_results
