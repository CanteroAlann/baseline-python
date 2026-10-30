from dataclasses import dataclass

from common.enums import MsgType
from common.message import Message


def non_negative(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


@dataclass
class CoordinatorState:
    outputs: dict[str, int]
    expected: int | None = None
    processed: int = 0

    def set_expected_count(self, expected: int | None) -> None:
        self.expected = non_negative(expected, "expected_messages")

    def record_done(self, output: str | None) -> None:
        if output is not None and output not in self.outputs:
            raise ValueError("Unknown article output")
        self.processed += 1
        if output is not None:
            self.outputs[output] += 1

    def is_complete(self) -> bool:
        if self.expected is None:
            return False
        if self.processed > self.expected:
            raise ValueError("More DONE messages than expected inputs")
        return self.processed == self.expected


class Coordinator:
    """Count DONE controls per session. emit waits for publisher confirms."""

    def __init__(self, emit, routing_keys=()):
        self.emit = emit
        self.routing_keys = tuple(routing_keys)
        self.sessions: dict[str, CoordinatorState] = {}

    def handle(self, message: Message):
        if not (message.is_input_eof() or message.is_done()):
            raise ValueError("Expected INPUT_EOF or DONE")
        session_id = message.session_id
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("session_id must be a nonempty string")
        state = self.sessions.setdefault(session_id, CoordinatorState(
            outputs=dict.fromkeys(self.routing_keys or ("output",), 0),
        ))
        if message.is_input_eof():
            state.set_expected_count(message.expected_messages)
        else:
            state.record_done(message.output)

        if not state.is_complete():
            return
        for output, count in state.outputs.items():
            route = output if self.routing_keys else session_id
            self.emit(Message(MsgType.EOF_RECORDS, session_id, expected_messages=count), route)
        del self.sessions[session_id]
