import re

from nltk.corpus import stopwords

from common.article.article import Article
from common.article.clean_article import CleanArticle
from common.article.external_article import ExternalArticle

WORD_REGEX = r'\b\w+\b'
NUMBER_REGEX = r'[+-]?((\d+\.?\d*)|(\.\d+))'
STOP_WORDS = set(stopwords.words("english")) | set(stopwords.words("french"))


def extract_non_stopwords_from_abstract(paragraph):
    if not isinstance(paragraph, str):
        return []
    words = re.findall(WORD_REGEX, paragraph.lower())
    return [word for word in words if word not in STOP_WORDS and not re.fullmatch(NUMBER_REGEX, word)]


class Preprocessor:
    def process(self, article: ExternalArticle) -> CleanArticle:
        words = extract_non_stopwords_from_abstract(article.data.get("abstract"))
        return article.to_clean_article(words)
