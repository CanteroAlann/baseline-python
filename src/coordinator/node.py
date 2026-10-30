from common.coordination import Coordinator
from common.message import Message
from common.message_protocol import internal


class CoordinatorNode:
    def __init__(self, input_queue, output_queue, routing_keys=()):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.coordinator = Coordinator(self.publish_eof, routing_keys)

    def publish_eof(self, message: Message, routing_key: str):
        body = internal.serialize(message)
        self.output_queue.send(body, routing_key=routing_key,
                               mandatory=bool(self.coordinator.routing_keys))

    def process_message(self, body, ack, nack):
        self.coordinator.handle(internal.deserialize(body))
        ack()

    def start(self):
        self.input_queue.start_consuming(self.process_message)
