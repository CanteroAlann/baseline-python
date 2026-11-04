from dataclasses import dataclass, field

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
    expected_by_input: dict[str, int] = field(default_factory=dict)

    def set_expected_count(self, expected: int | None) -> None:
        self.expected = non_negative(expected, "expected_messages")

    def record_done(self, output: str | None, produced_count: int = 1) -> None:
        produced_count = non_negative(produced_count, "produced_count")
        if output is not None and output not in self.outputs:
            raise ValueError("Unknown article output")
        self.processed += 1
        if output is not None:
            self.outputs[output] += produced_count

    def is_complete(self) -> bool:
        if self.expected is None:
            return False
        if self.processed > self.expected:
            raise ValueError("More DONE messages than expected inputs")
        return self.processed == self.expected


class Coordinator:
    """Count DONE controls per session. emit waits for publisher confirms."""

    def __init__(self, emit, routing_keys=(), *, independent_routes=False, expected_inputs=None,
                 input_routes=()):
        self.emit = emit
        self.routing_keys = tuple(routing_keys)
        self.independent_routes = independent_routes
        self.expected_inputs = non_negative(expected_inputs, "expected_inputs") if expected_inputs is not None else None
        self.input_routes = tuple(input_routes)
        if self.input_routes and (not independent_routes or not self.routing_keys or expected_inputs is not None):
            raise ValueError("Multiple input routes require independent outputs and dynamic input counts")
        self.sessions: dict[str | tuple[str, str], CoordinatorState] = {}

    def handle(self, message: Message):
        if not (message.is_input_eof() or message.is_done()):
            raise ValueError("Expected INPUT_EOF or DONE")
        session_id = message.session_id
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("session_id must be a nonempty string")
        if self.input_routes and message.is_input_eof():
            input_route = message.input_route
            if not isinstance(input_route, str) or input_route not in self.input_routes:
                raise ValueError("Expected a configured input_route on INPUT_EOF")
            expected = non_negative(message.expected_messages, "expected_messages")
            for output in self.routing_keys:
                key = (session_id, output)
                state = self.sessions.setdefault(key, CoordinatorState(outputs={output: 0}))
                state.expected_by_input[input_route] = expected
                if all(route in state.expected_by_input for route in self.input_routes):
                    state.set_expected_count(sum(state.expected_by_input.values()))
                self._complete(key, session_id, state)
            return
        session_key: str | tuple[str, str]
        if self.independent_routes:
            if not isinstance(message.output, str) or message.output not in self.routing_keys:
                raise ValueError("Expected a configured input route on DONE and INPUT_EOF")
            session_key = (session_id, message.output)
            outputs = (message.output,)
        else:
            session_key = session_id
            outputs = self.routing_keys or ("output",)
        state = self.sessions.setdefault(session_key, CoordinatorState(
            outputs=dict.fromkeys(outputs, 0),
            expected=self.expected_inputs,
        ))
        if message.is_input_eof():
            state.set_expected_count(message.expected_messages)
        else:
            state.record_done(message.output, message.produced_count if message.produced_count is not None else 1)

        self._complete(session_key, session_id, state)

    def _complete(self, session_key, session_id, state):
        if not state.is_complete():
            return
        for output, count in state.outputs.items():
            route = output if self.routing_keys else session_id
            self.emit(Message(MsgType.EOF_RECORDS, session_id, expected_messages=count), route)
        del self.sessions[session_key]
