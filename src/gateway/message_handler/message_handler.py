from common.enums import MsgType
import uuid

from common.article import CleanArticle
from common.message_protocol import internal


class MessageHandler:
    def __init__(self):
        self.session_id = uuid.uuid4().hex

    def serialize_data_message(self, article):
        return internal.serialize({
            "type": MsgType.ARTICLE_RECORD,
            "session_id": self.session_id,
            "article": article,
        })

    def serialize_eof_message(self):
        return internal.serialize({"type": MsgType.EOF_RECORDS, "session_id": self.session_id})

    def deserialize_result_message(self, body):
        message = internal.deserialize(body)
        if message["session_id"] != self.session_id:
            return None
        if "article" in message:
            message["article"] = CleanArticle.from_dict(message["article"])
        return message
