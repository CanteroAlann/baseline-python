from common.article import CleanArticle
from filters.filter_node import FilterNode


def filter_by_year(article: CleanArticle) -> bool:
    year = article.date_modified_year
    return year is not None and year <= 2020


class YearFilterNode(FilterNode):
    def __init__(self, input_queue, output_queue):
        super().__init__(input_queue, output_queue, filter_by_year)
