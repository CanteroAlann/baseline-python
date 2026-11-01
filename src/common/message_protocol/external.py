from common.enums import MsgType
from common import custom_socket
from common.article import ExternalArticle
from common.message import Message

from . import external_serializer as serializer
from . import internal

MAX_FIELD_SIZE = 64 * 1024 * 1024


def _recv_uint32(sock):
    return serializer.deserialize_uint32(custom_socket.recv_all(sock, serializer.UINT32_SIZE))


def _recv_string(sock):
    return serializer.deserialize_string(_recv_bytes(sock))


def _recv_bytes(sock):
    size = _recv_uint32(sock)
    if size > MAX_FIELD_SIZE:
        raise ValueError("Field exceeds maximum size")
    return custom_socket.recv_all(sock, size)


def _serialize_bytes(data):
    if len(data) > MAX_FIELD_SIZE:
        raise ValueError("Field exceeds maximum size")
    return serializer.serialize_uint32(len(data)) + data


def _serialize_string(value):
    return _serialize_bytes(serializer.serialize_string(value))


def _recv_article_record(sock):
    return ExternalArticle.deserialize(_recv_string(sock))


def _recv_article_results(sock):
    count = _recv_uint32(sock)
    results = []
    for _ in range(count):
        url = _recv_string(sock)
        date_modified = _recv_string(sock)
        results.append((url, date_modified))
    return results


def _recv_empty(sock):
    return None


def _recv_query_message(sock):
    return internal.deserialize(_recv_string(sock).encode("utf-8"))


def _send_query_message(sock, message: Message):
    custom_socket.send_all(sock, serializer.serialize_uint32(message.type)
                           + _serialize_bytes(internal.serialize(message)))


def _send_article_record(sock, article):
    message = serializer.serialize_uint32(MsgType.ARTICLE_RECORD)
    message += _serialize_bytes(article.serialize())
    custom_socket.send_all(sock, message)


def _send_article_results(sock, results):
    message = serializer.serialize_uint32(MsgType.ARTICLE_RESULTS)
    message += serializer.serialize_uint32(len(results))
    custom_socket.send_all(sock, message)
    for url, date_modified in results:
        custom_socket.send_all(sock, _serialize_string(url) + _serialize_string(date_modified))


def _send_ack(sock):
    custom_socket.send_all(sock, serializer.serialize_uint32(MsgType.ACK))


def _send_eof_records(sock):
    custom_socket.send_all(sock, serializer.serialize_uint32(MsgType.EOF_RECORDS))


RECV_MSG_HANDLERS = {
    MsgType.ARTICLE_RECORD: _recv_article_record,
    MsgType.ARTICLE_RESULTS: _recv_article_results,
    MsgType.ACK: _recv_empty,
    MsgType.EOF_RECORDS: _recv_empty,
    MsgType.QUERY_RESULT: _recv_query_message,
    MsgType.QUERY_EOF: _recv_query_message,
}

SEND_MSG_HANDLERS = {
    MsgType.ARTICLE_RECORD: _send_article_record,
    MsgType.ARTICLE_RESULTS: _send_article_results,
    MsgType.ACK: _send_ack,
    MsgType.EOF_RECORDS: _send_eof_records,
    MsgType.QUERY_RESULT: _send_query_message,
    MsgType.QUERY_EOF: _send_query_message,
}


def recv_msg(sock):
    msg_type = MsgType(_recv_uint32(sock))
    if msg_type not in RECV_MSG_HANDLERS:
        raise ValueError(f"Unknown message type: {msg_type}")
    payload = RECV_MSG_HANDLERS[msg_type](sock)
    if isinstance(payload, Message) and payload.type != msg_type:
        raise ValueError("Query frame type does not match its payload")
    return msg_type, payload


def send_msg(sock, msg_type, *args):
    if msg_type not in SEND_MSG_HANDLERS:
        raise ValueError(f"Unknown message type: {msg_type}")
    if args and isinstance(args[0], Message) and args[0].type != msg_type:
        raise ValueError("Query frame type does not match its payload")
    SEND_MSG_HANDLERS[msg_type](sock, *args)
