import re

from nltk.corpus import stopwords

WORD_REGEX = r'\b\w+\b'
NUMBER_REGEX = r'[+-]?((\d+\.?\d*)|(\.\d+))'
stop_words = set(stopwords.words("english")) | set(stopwords.words("french"))


def extract_non_stopwords_from_abstract(abstract):
    if not isinstance(abstract, str):
        return []
    words = re.findall(WORD_REGEX, abstract.lower())
    return [word for word in words if word not in stop_words and not re.fullmatch(NUMBER_REGEX, word)]


class Preprocessor:
    def process(self, article):
        words = extract_non_stopwords_from_abstract(article.data.get("abstract"))
        return article.to_clean_article(words)
