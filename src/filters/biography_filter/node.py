import logging

from common.article import ExternalArticle
from common.enums import MsgType
from common.message import Message
from common.message_protocol import internal
from common.article.external_article import has_biography_section, parse_field
from filters.filter_node import FilterNode


"""Devuelve True si el artículo tiene una sección de biography/biographie, False en caso contrario."""
def filter_by_biography(article: ExternalArticle) -> bool:
    has_bio = article.has_biography
    has_img = article.image_url is not None

    logging.info(f"AAA filter_by_biography: article={article.name!r}, ¿biography?={has_bio}, ¿image?={has_img}")
    return has_bio


class BiographyFilterNode(FilterNode):
    def __init__(self, input_queue, output_queue, coordinator_queue):
        super().__init__(input_queue, output_queue, filter_by_biography, coordinator_queue)

    def publish_message(self, body: bytes, message: Message):
        article = message.require_article()
        compact_article = ExternalArticle({
            "name": article.name,
            "url": article.url,
            "image": {"content_url": article.image_url},
        })
        # TODO: No hace falta que haya un msg type, total siempre irá al image fetcher. Por ahora lo dejo asi
        request = Message(
            MsgType.ARTICLE_RECORD,
            message.session_id,
            article_id=message.article_id,
            article=compact_article,
        )
        self.output_queue.send(internal.serialize(request))