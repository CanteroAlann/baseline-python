import logging

from common.article import ExternalArticle
from common.enums import MsgType
from common.message import Message
from common.message_protocol import internal


class FilterNode:
    def __init__(self, input_queue, output_queue, filter_function, control_queue):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.filter_function = filter_function
        self.control_queue = control_queue

    def process_message(self, body, ack, nack):
        message = internal.deserialize(body, ExternalArticle)
        logging.info(
            "%s received %s session=%s article_id=%s",
            type(self).__name__, message.type.name, message.session_id, message.article_id,
        )
        if message.is_eof():
            control = Message(MsgType.INPUT_EOF, message.session_id,
                              expected_messages=message.expected_messages)
        elif message.is_article():
            # waits before publishing DONE.
            output = self.process_article(message)
            control = Message(MsgType.DONE, message.session_id, output=output)
        else:
            raise ValueError("Expected ARTICLE_RECORD or EOF_RECORDS")
        self.control_queue.send(internal.serialize(control))
        logging.info(
            "%s sent %s to coordinator session=%s article_id=%s expected_messages=%s",
            type(self).__name__, control.type.name, message.session_id,
            message.article_id, control.expected_messages,
        )
        ack()

    def process_article(self, message: Message) -> str | None:
        article = message.require_article()
        if not self.filter_function(article):
            if logging.getLogger().isEnabledFor(logging.INFO):
                logging.info(
                    "%s discarded article session=%s article_id=%s name=%r language=%r",
                    type(self).__name__, message.session_id, message.article_id,
                    article.name, article.in_language,
                )
            return None
        self.publish_message(internal.serialize(message), message)
        if logging.getLogger().isEnabledFor(logging.INFO):
            logging.info(
                "%s forwarded article session=%s article_id=%s name=%r language=%r",
                type(self).__name__, message.session_id, message.article_id,
                article.name, article.in_language,
            )
        return "output"

    def publish_message(self, body: bytes, message: Message):
        self.output_queue.send(body)

    def start(self):
        self.input_queue.start_consuming(self.process_message)
