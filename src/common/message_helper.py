from abc import ABC, abstractmethod

from common.coordination import CoordinatorState
from common.message import Message
from common.message_protocol import internal


class MessageHelper(ABC):
    def __init__(self, incoming, emit):
        self.input_queue = incoming
        self.emit = emit

    def process_message(self, body, ack, nack):
        self.handle(internal.deserialize(body))
        ack()

    def start(self):
        self.input_queue.start_consuming(self.process_message)

    @abstractmethod
    def handle(self, message: Message):
        pass


def input_state():
    return CoordinatorState(outputs={})
