from common.enums import MsgType, QUERY_COUNT
from csv import DictReader, field_size_limit
import logging
from pathlib import Path
import socket
import sys
import time
import base64
import json
import re

from common.article import ExternalArticle
from common.message import Message
from common.message_protocol import external as protocol

DEFAULT_TIMEOUT = 1800
CSV_ENCODING = "utf-8-sig"

CLIENT_SLEEP_TIME = 0.2  # seconds

OUTPUT_DIR = Path("/output")


def _detect_image_extension(data: bytes) -> str:
        if data.startswith(b"\xff\xd8\xff"):
            return ".jpg"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if data[:6] in (b"GIF87a", b"GIF89a"):
            return ".gif"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return ".webp"
        if data.startswith(b"BM"):
            return ".bmp"
        stripped = data.lstrip()
        if stripped.startswith(b"<"):
            return ".svg"
        return ".bin"

def _safe_filename(name: str, fallback: str) -> str:
    name = re.sub(r"[^\w\-.]+", "_", name or "").strip("_")
    return name or fallback


def _result_for_log(result):
    if isinstance(result, dict) and result.get("image_bytes"):
        return {**result, "image_bytes": f"<{len(result['image_bytes'])} base64 characters>"}
    return result


class Client:
    def save_results(self, final_results, output_dir: Path = OUTPUT_DIR):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # resumen txt
        txt_path = output_dir / "results.txt"
        with txt_path.open("w", encoding="utf-8") as f:
            for query_id in sorted(final_results.keys()):
                items = final_results[query_id]
                f.write(f"=== Query {query_id} ({len(items)} resultados) ===\n")
                for idx, item in enumerate(items):
                    if isinstance(item, dict) and "image_bytes" in item:
                        # no volcar el base64 gigante al txt
                        summary = {k: v for k, v in item.items() if k != "image_bytes"}
                        summary["image_bytes"] = (
                            f"<guardada en images/{idx:04d}_*.EXT>"
                            if item["image_bytes"] else None
                        )
                        f.write(json.dumps(summary, ensure_ascii=False) + "\n")
                    else:
                        f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")
                f.write("\n")
        logging.info("Saved %s", txt_path)

        # imagenes
        q2 = final_results.get(2, [])
        if q2:
            images_dir = output_dir / "images"
            images_dir.mkdir(exist_ok=True)
            for idx, item in enumerate(q2):
                if not isinstance(item, dict):
                    continue
                b64 = item.get("image_bytes")
                if not b64:
                    continue
                try:
                    raw = base64.b64decode(b64)
                except Exception as exc:
                    logging.warning("No se pudo decodificar imagen idx=%s: %s", idx, exc)
                    continue
                ext = _detect_image_extension(raw)
                stem = _safe_filename(item.get("name"), f"img_{idx}")
                path = images_dir / f"{idx:04d}_{stem}{ext}"
                path.write_bytes(raw)
                logging.info("Saved image %s (%d bytes)", path, len(raw))



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
            
            count=0
            for article in reader:
                if None in article or any(value is None for value in article.values()):
                    raise ValueError(f"{file_path}: malformed CSV record")

                # logging.info("Sending article record: %s", article)
                count+=1
                
                protocol.send_msg(self.server_socket, MsgType.ARTICLE_RECORD, ExternalArticle(article))
            logging.info("Amount of records sent: %d", count)
        
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
                logging.info("Received Query %s partial result: %s", query_id, _result_for_log(message.result))
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
                         len(records), [_result_for_log(value) for value in final_results[query_id]])
        return final_results
