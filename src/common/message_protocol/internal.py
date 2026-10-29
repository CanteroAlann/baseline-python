import json

from common.enums import MsgType
from common.article import CleanArticle, ExternalArticle
from common.message import Message


def serialize(message: Message) -> bytes:
    return json.dumps(message.to_dict(), ensure_ascii=False).encode("utf-8")


def deserialize(
    message: bytes, article_type: type[ExternalArticle] | type[CleanArticle] = ExternalArticle,
) -> Message:
    data = json.loads(message.decode("utf-8"))
    data["type"] = MsgType(data["type"])
    if "article" in data:
        data["article"] = article_type.from_dict(data["article"])
    return Message(**data)
