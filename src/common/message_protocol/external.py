import json

from common import custom_socket

from . import external_serializer as serializer

MAX_FIELD_SIZE = 64 * 1024 * 1024


class MsgType:
    ARTICLE_RECORD = 1
    ARTICLE_NAMES = 2
    ACK = 3
    EOF_RECORDS = 4


def _recv_uint32(sock):
    return serializer.deserialize_uint32(custom_socket.recv_all(sock, serializer.UINT32_SIZE))


def _recv_string(sock):
    size = _recv_uint32(sock)
    if size > MAX_FIELD_SIZE:
        raise ValueError("Field exceeds maximum size")
    return serializer.deserialize_string(custom_socket.recv_all(sock, size))


def _serialize_string(value):
    data = serializer.serialize_string(value)
    if len(data) > MAX_FIELD_SIZE:
        raise ValueError("Field exceeds maximum size")
    return serializer.serialize_uint32(len(data)) + data


def _recv_article_record(sock):
    article = json.loads(_recv_string(sock))
    if not isinstance(article, dict) or "name" not in article:
        raise ValueError("Article must contain a name")
    for value in article.values():
        if not isinstance(value, str):
            raise ValueError("Article fields must be strings")
    return article


def _recv_article_names(sock):
    count = _recv_uint32(sock)
    names = []
    for _ in range(count):
        names.append(_recv_string(sock))
    return names


def _recv_empty(sock):
    return None


def _send_article_record(sock, article):
    message = serializer.serialize_uint32(MsgType.ARTICLE_RECORD)
    message += _serialize_string(json.dumps(article, ensure_ascii=False))
    custom_socket.send_all(sock, message)


def _send_article_names(sock, names):
    message = serializer.serialize_uint32(MsgType.ARTICLE_NAMES)
    message += serializer.serialize_uint32(len(names))
    custom_socket.send_all(sock, message)
    for name in names:
        custom_socket.send_all(sock, _serialize_string(name))


def _send_ack(sock):
    custom_socket.send_all(sock, serializer.serialize_uint32(MsgType.ACK))


def _send_eof_records(sock):
    custom_socket.send_all(sock, serializer.serialize_uint32(MsgType.EOF_RECORDS))


RECV_MSG_HANDLERS = {
    MsgType.ARTICLE_RECORD: _recv_article_record,
    MsgType.ARTICLE_NAMES: _recv_article_names,
    MsgType.ACK: _recv_empty,
    MsgType.EOF_RECORDS: _recv_empty,
}

SEND_MSG_HANDLERS = {
    MsgType.ARTICLE_RECORD: _send_article_record,
    MsgType.ARTICLE_NAMES: _send_article_names,
    MsgType.ACK: _send_ack,
    MsgType.EOF_RECORDS: _send_eof_records,
}


def recv_msg(sock):
    msg_type = _recv_uint32(sock)
    if msg_type not in RECV_MSG_HANDLERS:
        raise ValueError(f"Unknown message type: {msg_type}")
    return msg_type, RECV_MSG_HANDLERS[msg_type](sock)


def send_msg(sock, msg_type, *args):
    if msg_type not in SEND_MSG_HANDLERS:
        raise ValueError(f"Unknown message type: {msg_type}")
    SEND_MSG_HANDLERS[msg_type](sock, *args)
