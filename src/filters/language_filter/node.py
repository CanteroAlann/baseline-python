from common.article import ExternalArticle
from filters.filter_node import FilterNode


def filter_by_language(article: ExternalArticle) -> bool:
    return article.in_language is not None and article.in_language.lower() == "en"


class LanguageFilterNode(FilterNode):
    def __init__(self, input_queue, output_queue):
        super().__init__(input_queue, output_queue, filter_by_language)
