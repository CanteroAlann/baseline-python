import base64
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from common.article import ExternalArticle
from common.enums import MsgType
from common.message_protocol import internal
from common.article.external_article import parse_field

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
    def __init__(self, input_queue, output_exchange):
        self.input_queue = input_queue
        self.output_exchange = output_exchange
        self.opener = build_opener(WikimediaRedirectHandler())

    def fetch_image(self, image_url):
        parsed = urlparse(image_url)
        
        return image_bytes

    def process_message(self, body, ack, nack):
        message = internal.deserialize(body, ExternalArticle)
        message_type = message["type"]
        article = message.get("article")
        article_name = article.name if article is not None else None

        logging.info(
            "ImageFetcherNode received message type=%s session=%s name=%r",
            message_type, message["session_id"], article_name,
        )

        image = parse_field(article.data.get("image"), {})
        image_url = image.get("content_url") if isinstance(image, dict) else None
        if not image_url:
            logging.info(
                "ImageFetcherNode skipped article without image session=%s name=%r",
                message["session_id"], article.name,
            )
            ack()
            return

        try:
            image_bytes = self.fetch_image(image_url)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            logging.warning(
                "ImageFetcherNode failed session=%s name=%r url=%s error=%s",
                message["session_id"], article.name, image_url, exc,
            )
            ack()
            return

        result = {
            "type": MsgType.Q2_RESULT,
            "session_id": message["session_id"],
            "name": article.name,
            "url": article.url,
            "image_bytes": base64.b64encode(image_bytes).decode("ascii"),
        }
        self.output_exchange.send(
            internal.serialize(result), routing_key=message["session_id"], mandatory=False,
        )
        ack()

    def start(self):
        self.input_queue.start_consuming(self.process_message)