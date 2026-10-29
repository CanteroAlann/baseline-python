import logging

from common.article import ExternalArticle
from common.enums import MsgType
from common.message_protocol import internal
from common.article.external_article import has_biography_section, parse_field
from filters.filter_node import FilterNode


"""Devuelve True si el artículo tiene una sección de biography/biographie, False en caso contrario."""
def filter_by_biography(article: ExternalArticle) -> bool:
    sections = parse_field(article.data.get("sections"), [])
    logging.info("AAA filter_by_biography: article=%r sections=%r", article.name, sections)
    if not isinstance(sections, list):
        return False
    return has_biography_section(sections)


class BiographyFilterNode(FilterNode):
    def __init__(self, input_queue, output_queue):
        super().__init__(input_queue, output_queue, filter_by_biography)

    def publish_message(self, body, message):
        if message["type"] == MsgType.EOF_RECORDS:
            self.output_queue.send(body)
            return

        article = message["article"]
        image = parse_field(article.data.get("image"), {})
        image_url = image.get("content_url") if isinstance(image, dict) else None
        if not image_url:
            logging.info(
                "BiographyFilterNode skipped article without image session=%s name=%r",
                message["session_id"], article.name,
            )
            return

        article_for_image_fetcher = {
            "name": article.name,
            "url": article.url,
            "image": {"content_url": image_url},
        }
        # TODO: No hace falta que haya un msg type, total siempre irá al image fetcher. Por ahora lo dejo asi
        request = {
            "type": MsgType.ARTICLE_RECORD,
            "session_id": message["session_id"],
            "article": article_for_image_fetcher,
        }
        self.output_queue.send(internal.serialize(request))