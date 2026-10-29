from common.article import CleanArticle, ExternalArticle
from common.message import Message
from filters.filter_node import FilterNode


def filter_by_language(article: ExternalArticle | CleanArticle) -> bool:
    return article.in_language is not None and article.in_language.lower() == "en"


class LanguageFilterNode(FilterNode):
    def __init__(self, input_queue, output_queue, coordinator_queue):
        super().__init__(input_queue, output_queue, filter_by_language, coordinator_queue)

    def publish_message(self, body: bytes, message: Message):
        # The gateway deletes private queue when the session ends. Discard unroutable late replies
        self.output_queue.send(body, routing_key=message.session_id, mandatory=False)
