MAX_FIELD_SIZE = 64 * 1024 * 1024
UINT32_SIZE = 4

_NONE = b"n"
_BOOL = b"b"
_INT = b"i"
_FLOAT = b"f"
_STRING = b"s"
_BYTES = b"y"
_LIST = b"l"
_TUPLE = b"t"
_SET = b"e"
_DICT = b"d"


def _uint32(value: int) -> bytes:
    return value.to_bytes(UINT32_SIZE, byteorder="big", signed=False)


def _read_uint32(data: bytes, offset: int) -> tuple[int, int]:
    end = offset + UINT32_SIZE
    if end > len(data):
        raise ValueError("Unexpected end of binary message")
    return int.from_bytes(data[offset:end], byteorder="big", signed=False), end


def _field(value: bytes) -> bytes:
    if len(value) > MAX_FIELD_SIZE:
        raise ValueError("Binary message field exceeds maximum size")
    return _uint32(len(value)) + value


def _read_field(data: bytes, offset: int) -> tuple[bytes, int]:
    size, offset = _read_uint32(data, offset)
    if size > MAX_FIELD_SIZE:
        raise ValueError("Binary message field exceeds maximum size")
    end = offset + size
    if end > len(data):
        raise ValueError("Unexpected end of binary message")
    return data[offset:end], end


def _encode(value) -> bytes:
    if value is None:
        return _NONE
    if isinstance(value, bool):
        return _BOOL + (b"\x01" if value else b"\x00")
    if isinstance(value, int):
        encoded = value.to_bytes(max(1, (value.bit_length() + 8) // 8), byteorder="big", signed=True)
        return _INT + _field(encoded)
    if isinstance(value, float):
        return _FLOAT + _field(value.hex().encode("ascii"))
    if isinstance(value, str):
        return _STRING + _field(value.encode("utf-8"))
    if isinstance(value, bytes):
        return _BYTES + _field(value)
    if isinstance(value, list):
        return _LIST + _field(b"".join(_encode(item) for item in value))
    if isinstance(value, tuple):
        return _TUPLE + _field(b"".join(_encode(item) for item in value))
    if isinstance(value, set):
        return _SET + _field(b"".join(_encode(item) for item in sorted(value)))
    if isinstance(value, dict):
        payload = b"".join(_encode(key) + _encode(item) for key, item in value.items())
        return _DICT + _field(_uint32(len(value)) + payload)
    raise TypeError(f"Unsupported value in binary message: {type(value).__name__}")


def _decode(data: bytes, offset: int = 0):
    if offset >= len(data):
        raise ValueError("Unexpected end of binary message")
    tag = data[offset:offset + 1]
    offset += 1
    if tag == _NONE:
        return None, offset
    if tag == _BOOL:
        if offset >= len(data) or data[offset] not in (0, 1):
            raise ValueError("Invalid boolean in binary message")
        return data[offset] == 1, offset + 1
    if tag in (_INT, _FLOAT, _STRING, _BYTES):
        value, offset = _read_field(data, offset)
        if tag == _INT:
            return int.from_bytes(value, byteorder="big", signed=True), offset
        if tag == _FLOAT:
            return float.fromhex(value.decode("ascii")), offset
        if tag == _STRING:
            return value.decode("utf-8"), offset
        return value, offset
    if tag in (_LIST, _TUPLE, _SET):
        payload, offset = _read_field(data, offset)
        values = []
        payload_offset = 0
        while payload_offset < len(payload):
            value, payload_offset = _decode(payload, payload_offset)
            values.append(value)
        if tag == _TUPLE:
            return tuple(values), offset
        if tag == _SET:
            return set(values), offset
        return values, offset
    if tag == _DICT:
        payload, offset = _read_field(data, offset)
        count, payload_offset = _read_uint32(payload, 0)
        result = {}
        for _ in range(count):
            key, payload_offset = _decode(payload, payload_offset)
            value, payload_offset = _decode(payload, payload_offset)
            result[key] = value
        if payload_offset != len(payload):
            raise ValueError("Trailing data in binary dictionary")
        return result, offset
    raise ValueError(f"Unknown binary message tag: {tag!r}")


def serialize(data: dict) -> bytes:
    return _encode(data)


def deserialize(data: bytes) -> dict:
    value, offset = _decode(data)
    if offset != len(data) or not isinstance(value, dict):
        raise ValueError("Invalid binary internal message")
    return value
