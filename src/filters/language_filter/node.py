from common.article import ExternalArticle
from filters.filter_node import FilterNode


def filter_by_language(article: ExternalArticle) -> bool:
    return article.in_language is not None and article.in_language.lower() == "en"


class LanguageFilterNode(FilterNode):
    def __init__(self, input_queue, output_queue):
        super().__init__(input_queue, output_queue, filter_by_language)

    def publish_message(self, body, message):
        # The gateway deletes its private queue when the session ends.
        # Discard unroutable late replies so other sessions can keep being processed.
        self.output_queue.send(body, routing_key=message["session_id"], mandatory=False)
