UINT32_SIZE = 4


def serialize_uint32(value):
    return value.to_bytes(UINT32_SIZE, byteorder="big", signed=False)


def deserialize_uint32(data):
    return int.from_bytes(data, byteorder="big", signed=False)


def serialize_string(value):
    return value.encode("utf-8")


def deserialize_string(data):
    return data.decode("utf-8")
