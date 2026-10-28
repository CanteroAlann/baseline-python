import json

from common.enums import MsgType


def serialize(message):
    return json.dumps(
        message, ensure_ascii=False, default=lambda article: article.to_dict()
    ).encode("utf-8")


def deserialize(message, article_type=None):
    data = json.loads(message.decode("utf-8"))
    data["type"] = MsgType(data["type"])
    if article_type is not None and "article" in data:
        data["article"] = article_type.from_dict(data["article"])
    return data
