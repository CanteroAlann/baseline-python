import os
import json

from common.enums import MsgType
from common.article import CleanArticle, ExternalArticle
from common.message import Message


def _serialize_json(message: Message) -> bytes:
    return json.dumps(message.to_dict(), ensure_ascii=False).encode("utf-8")


def _deserialize_json(message: bytes) -> dict:
    return json.loads(message.decode("utf-8"))


def _deserialize_message(
    data: dict, article_type: type[ExternalArticle] | type[CleanArticle],
) -> Message:
    data["type"] = MsgType(data["type"])
    if "article" in data:
        data["article"] = article_type.from_dict(data["article"])
    return Message(**data)


def _serialize_binary(message: Message) -> bytes:
    from . import internal_binary

    return internal_binary.serialize(message.to_dict())


def _deserialize_binary(message: bytes) -> dict:
    from . import internal_binary

    return internal_binary.deserialize(message)


_SERIALIZER = os.environ.get("INTERNAL_SERIALIZER", "json").strip().lower()
if _SERIALIZER == "json":
    _serialize = _serialize_json
    _deserialize = _deserialize_json
elif _SERIALIZER == "binary":
    _serialize = _serialize_binary
    _deserialize = _deserialize_binary
else:
    raise ValueError("INTERNAL_SERIALIZER must be either 'json' or 'binary'")


def serialize(message: Message) -> bytes:
    return _serialize(message)


def deserialize(
    message: bytes, article_type: type[ExternalArticle] | type[CleanArticle] = ExternalArticle,
) -> Message:
    return _deserialize_message(_deserialize(message), article_type)
