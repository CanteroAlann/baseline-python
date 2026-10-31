from common.enums import MsgType
import uuid

from common.article import ExternalArticle
from common.message import Message
from common.message_protocol import internal


class MessageHandler:
    def __init__(self):
        self.session_id = uuid.uuid4().hex
        self.article_count = 0

    def serialize_data_message(self, article: ExternalArticle) -> bytes:
        body = internal.serialize(Message(
            MsgType.ARTICLE_RECORD, self.session_id,
            article_id=self.article_count, article=article,
        ))
        self.article_count += 1
        return body

    def serialize_eof_message(self) -> bytes:
        return internal.serialize(Message(
            MsgType.EOF_RECORDS, self.session_id, expected_messages=self.article_count,
        ))

    def deserialize_result_message(self, body: bytes) -> Message | None:
        message = internal.deserialize(body)
        if message.session_id != self.session_id:
            return None
        return message
