import logging

from common.article import ExternalArticle
from common.message_protocol import internal
from .preprocess import Preprocessor


class PreprocessNode:
    def __init__(self, input_queue, output_queue):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.preprocessor = Preprocessor()

    def process_message(self, body, ack, nack):
        message = internal.deserialize(body, ExternalArticle)
        if message.is_article():
            article = message.require_article()
            if not isinstance(article, ExternalArticle):
                raise ValueError("Preprocessing requires an external article")
            logging.info(
                "Received article session=%s name=%r",
                message.session_id, article.name,
            )
            processed_article = self.preprocessor.process(article)
            message.article = processed_article
            logging.info(
                "Processed article session=%s name=%r abstract_word_count=%d unique_words=%d",
                message.session_id, processed_article.name,
                processed_article.abstract_word_count, len(processed_article.abstract),
            )
        elif not message.is_eof():
            raise ValueError("Expected ARTICLE_RECORD or EOF_RECORDS")
        self.output_queue.send(internal.serialize(message))
        logging.info(
            "Published %s to filters session=%s",
            message.type.name, message.session_id,
        )
        ack()

    def start(self):
        self.input_queue.start_consuming(self.process_message)
