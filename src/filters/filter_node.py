from common.article import ExternalArticle
from common.enums import MsgType
from common.message import Message
from common.message_protocol import internal


class FilterNode:
    def __init__(self, input_queue, output_queue, filter_function, coordinator_queue):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.filter_function = filter_function
        self.coordinator_queue = coordinator_queue

    def process_message(self, body, ack, nack):
        message = internal.deserialize(body, ExternalArticle)
        if message.is_eof():
            control = Message(MsgType.INPUT_EOF, message.session_id,
                              expected_messages=message.expected_messages)
        elif message.is_article():
            # waits before publishing DONE.
            output = self.process_article(message)
            control = Message(MsgType.DONE, message.session_id, output=output)
        else:
            raise ValueError("Expected ARTICLE_RECORD or EOF_RECORDS")
        self.coordinator_queue.send(internal.serialize(control))
        ack()

    def process_article(self, message: Message) -> str | None:
        if not self.filter_function(message.require_article()):
            return None
        self.publish_message(internal.serialize(message), message)
        return "output"

    def publish_message(self, body: bytes, message: Message):
        self.output_queue.send(body)

    def start(self):
        self.input_queue.start_consuming(self.process_message)
