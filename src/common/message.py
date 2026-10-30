from dataclasses import dataclass
from typing import Any

from common.article import CleanArticle, ExternalArticle
from common.enums import MsgType, QUERY_IDS


@dataclass
class Message:
    type: MsgType
    session_id: str
    article: ExternalArticle | CleanArticle | None = None
    article_id: int | None = None
    expected_messages: int | None = None
    output: str | None = None
    query_id: int | None = None
    result: Any = None

    def is_article(self) -> bool:
        return self.type == MsgType.ARTICLE_RECORD

    def is_eof(self) -> bool:
        return self.type == MsgType.EOF_RECORDS

    def is_input_eof(self) -> bool:
        return self.type == MsgType.INPUT_EOF

    def is_done(self) -> bool:
        return self.type == MsgType.DONE

    def is_query_result(self) -> bool:
        return self.type == MsgType.QUERY_RESULT

    def is_query_eof(self) -> bool:
        return self.type == MsgType.QUERY_EOF

    def require_query_id(self) -> int:
        if type(self.query_id) is not int or self.query_id not in QUERY_IDS:
            raise ValueError("query_id must be between 1 and 5")
        return self.query_id

    def require_article(self) -> ExternalArticle | CleanArticle:
        if self.article is None:
            raise ValueError("Expected a message containing an article")
        return self.article

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"type": self.type, "session_id": self.session_id}
        if self.article is not None:
            data["article"] = self.article.to_dict()
        if self.article_id is not None:
            data["article_id"] = self.article_id
        if self.expected_messages is not None:
            data["expected_messages"] = self.expected_messages
        if self.is_done():
            data["output"] = self.output
        if self.query_id is not None:
            data["query_id"] = self.query_id
        if self.is_query_result():
            data["result"] = self.result
        return data
