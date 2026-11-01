from common.article import CleanArticle, ExternalArticle
from common.message import Message
from common.enums import MsgType
from common.message_protocol import internal
from filters.filter_node import FilterNode


def filter_by_language(article: ExternalArticle | CleanArticle) -> bool:
    return article.in_language is not None and article.in_language.lower() == "en"


class LanguageFilterNode(FilterNode):
    def __init__(self, input_queue, output_queue, control_queue):
        super().__init__(input_queue, output_queue, filter_by_language, control_queue)

    def publish_message(self, body: bytes, message: Message):
        article = message.require_article()
        result = Message(MsgType.QUERY_RESULT, query_id=1,
                         article_id=message.article_id,
                         result={"url": article.url, "date_modified": article.date_modified})
        # The gateway deletes private queue when the session ends. Discard unroutable late replies
        self.output_queue.send(internal.serialize(result), routing_key=message.session_id, mandatory=False)
