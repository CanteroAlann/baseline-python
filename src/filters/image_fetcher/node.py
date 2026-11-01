import base64
import logging
import os
from concurrent.futures import ThreadPoolExecutor, wait
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from common.article import ExternalArticle
from common.enums import MsgType
from common.message import Message
from common.message_protocol import internal

IMAGE_FETCH_TIMEOUT = float(os.getenv("IMAGE_FETCH_TIMEOUT", "15"))
IMAGE_MAX_BYTES = int(os.getenv("IMAGE_MAX_BYTES", str(20 * 1024 * 1024)))
ALLOWED_IMAGE_HOST = "upload.wikimedia.org"


class WikimediaRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        parsed = urlparse(new_url)
        if parsed.scheme != "https" or parsed.hostname != ALLOWED_IMAGE_HOST:
            raise URLError("Image redirect is outside upload.wikimedia.org")
        return super().redirect_request(request, response, code, message, headers, new_url)


class ImageFetcherNode:
    def __init__(self, input_queue, output_exchange, control_queue):
        self.input_queue = input_queue
        self.output_exchange = output_exchange
        self.control_queue = control_queue
        self.opener = build_opener(WikimediaRedirectHandler())

    def fetch_image(self, image_url):
        # Only HTTP runs in the thread. Pika stays on the consuming thread.
        with ThreadPoolExecutor(max_workers=1) as executor:
            download = executor.submit(self.download_image, image_url)
            while True:
                finished, _ = wait((download,), timeout=1)
                self.input_queue.process_events()
                if finished:
                    return download.result()

    def download_image(self, image_url):
        parsed = urlparse(image_url)
        if parsed.scheme != "https" or parsed.hostname != ALLOWED_IMAGE_HOST:
            raise ValueError("Image URL must use HTTPS on upload.wikimedia.org")

        request = Request(image_url, headers={"User-Agent": "WikipediaArticleAnalysis/1.0"})
        with self.opener.open(request, timeout=IMAGE_FETCH_TIMEOUT) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > IMAGE_MAX_BYTES:
                raise ValueError("Image exceeds configured maximum size")
            image_bytes = response.read(IMAGE_MAX_BYTES + 1)
        if len(image_bytes) > IMAGE_MAX_BYTES:
            raise ValueError("Image exceeds configured maximum size")
        return image_bytes

    def build_result(self, message: Message, image_bytes):
        article = message.require_article()

        return Message(
            MsgType.QUERY_RESULT,
            article_id=message.article_id,
            query_id=2,
            result={
                "name": article.name,
                "url": article.url,
                "image_bytes": (
                    base64.b64encode(image_bytes).decode("ascii")
                    if image_bytes is not None else None
                ),
            },
        )

    def publish_result(self, message: Message, image_bytes):
        result = self.build_result(message, image_bytes)
        self.output_exchange.send(
            internal.serialize(result),
            routing_key=message.session_id,
            mandatory=False,
        )

    def process_article(self, message: Message):
        article = message.require_article()
        if not isinstance(article, ExternalArticle):
            raise ValueError("Image fetching requires an ExternalArticle")
        image_url = article.image_url
        image_bytes = None

        if image_url:
            try:
                image_bytes = self.fetch_image(image_url)
            except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                logging.warning(
                    "Image download failed session=%s article_id=%s error=%s",
                    message.session_id, message.article_id, exc,
                )

        self.publish_result(message, image_bytes)

    def process_message(self, body, ack, nack):
        message = internal.deserialize(body, ExternalArticle)

        if message.is_eof():
            control = Message(MsgType.INPUT_EOF, message.session_id,
                              expected_messages=message.expected_messages)
        elif message.is_article():
            logging.info("ImageFetcherNode received article session=%s article_id=%s",
                         message.session_id, message.article_id)
            self.process_article(message)
            control = Message(MsgType.DONE, message.session_id, output="output")
        else:
            raise ValueError("Expected ARTICLE_RECORD or EOF_RECORDS")

        self.control_queue.send(internal.serialize(control))
        ack()

    def start(self):
        self.input_queue.start_consuming(self.process_message)
