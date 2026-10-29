from common.enums import MsgType
from common.message import Message


def non_negative(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


class Coordinator:
    """Count DONE controls per session. emit waits for publisher confirms."""

    def __init__(self, emit, routing_keys=()):
        self.emit = emit
        self.routing_keys = tuple(routing_keys)
        self.sessions = {}

    def handle(self, message: Message):
        if not (message.is_input_eof() or message.is_done()):
            raise ValueError("Expected INPUT_EOF or DONE")
        session_id = message.session_id
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("session_id must be a nonempty string")
        state = self.sessions.setdefault(session_id, {
            "expected": None, "processed": 0,
            "outputs": dict.fromkeys(self.routing_keys or ("output",), 0),
        })
        if message.is_input_eof():
            state["expected"] = non_negative(message.expected_messages, "expected_messages")
        else:
            output = message.output
            if output is not None and output not in state["outputs"]:
                raise ValueError("Unknown article output")
            state["processed"] += 1
            if output is not None:
                state["outputs"][output] += 1

        if state["expected"] is None:
            return
        if state["processed"] > state["expected"]:
            raise ValueError("More DONE messages than expected inputs")
        if state["processed"] != state["expected"]:
            return
        for output, count in state["outputs"].items():
            route = output if self.routing_keys else session_id
            self.emit(Message(MsgType.EOF_RECORDS, session_id, expected_messages=count), route)
        del self.sessions[session_id]
