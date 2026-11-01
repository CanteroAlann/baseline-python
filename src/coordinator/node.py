from common.coordination import Coordinator
from common.message import Message
from common.enums import MsgType
from common.message_protocol import internal


class CoordinatorNode:
    def __init__(self, input_queue, output_queue, routing_keys=(), query_id=None, *, independent_routes=False,
                 expected_inputs=None):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.coordinator = Coordinator(self.publish_eof, routing_keys, independent_routes=independent_routes,
                                       expected_inputs=expected_inputs)
        self.query_id = query_id

    def publish_eof(self, message: Message, routing_key: str):
        if self.query_id is not None:
            message = Message(MsgType.QUERY_EOF, query_id=self.query_id,
                              expected_messages=message.expected_messages)
        body = internal.serialize(message)
        self.output_queue.send(body, routing_key=routing_key,
                               mandatory=bool(self.coordinator.routing_keys))

    def process_message(self, body, ack, nack):
        self.coordinator.handle(internal.deserialize(body))
        ack()

    def start(self):
        self.input_queue.start_consuming(self.process_message)
