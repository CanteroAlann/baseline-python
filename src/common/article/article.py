from abc import ABC, abstractmethod
import json
from typing import Any, Self


class Article(ABC):
    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        pass

    def serialize(self) -> bytes:
        return json.dumps(self.to_dict(), ensure_ascii=False).encode("utf-8")

    @classmethod
    def deserialize(cls, message: bytes | str) -> Self:
        return cls.from_dict(json.loads(message))
