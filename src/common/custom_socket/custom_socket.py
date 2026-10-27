
def recv_all(sock, size):
    if size < 0:
        raise ValueError("Receive size must be nonnegative")
    data = bytearray()
    while len(data) < size:
        try:
            chunk = sock.recv(size - len(data))
        except InterruptedError:
            continue
        if not chunk:
            raise EOFError(f"Connection closed after receiving {len(data)} of {size} bytes")
        data.extend(chunk)
    return bytes(data)


def send_all(sock, data):
    sent = 0
    while sent < len(data):
        try:
            count = sock.send(data[sent:])
        except InterruptedError:
            continue
        if count == 0:
            raise ConnectionError(f"Connection stopped after sending {sent} of {len(data)} bytes")
        sent += count
    return sent
