import socket
import time


class ClientSocket:

    def __init__(self, sock, process_events, timeout):
        if timeout <= 0:
            raise ValueError("Socket timeout must be positive")
        self.socket = sock
        self.process_events = process_events
        self.timeout = timeout

    def recv(self, size):
        return self._transfer(lambda: self.socket.recv(size))

    def send(self, data):
        return self._transfer(lambda: self.socket.send(data))

    def _transfer(self, operation):
        deadline = time.monotonic() + self.timeout
        while True:
            self.process_events()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise socket.timeout("Client socket operation timed out")
            self.socket.settimeout(min(1.0, remaining))
            try:
                return operation()
            except socket.timeout:
                continue
