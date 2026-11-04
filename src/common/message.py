from dataclasses import dataclass
from typing import Any

from common.article import CleanArticle, ExternalArticle
from common.enums import MsgType, QUERY_IDS


@dataclass
class Message:
    type: MsgType
    session_id: str = ""
    article: ExternalArticle | CleanArticle | None = None
    article_id: int | None = None
    expected_messages: int | None = None
    output: str | None = None
    query_id: int | None = None
    result: Any = None
    shard_id: int | None = None
    word_count: int | None = None
    url: str | None = None
    partial_sum: int | None = None
    partial_count: int | None = None
    average: float | None = None
    produced_count: int | None = None
    word: str | None = None
    input_route: str | None = None

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

    def is_word_count(self) -> bool:
        return self.type == MsgType.WORD_COUNT

    def is_hist_partial(self) -> bool:
        return self.type == MsgType.HIST_PARTIAL

    def is_avg_ready(self) -> bool:
        return self.type == MsgType.AVG_READY

    def require_query_id(self) -> int:
        if type(self.query_id) is not int or self.query_id not in QUERY_IDS:
            raise ValueError("query_id must be between 1 and 5")
        return self.query_id

    def require_article(self) -> ExternalArticle | CleanArticle:
        if self.article is None:
            raise ValueError("Expected a message containing an article")
        return self.article

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"type": self.type}
        if not (self.is_query_result() or self.is_query_eof()):
            data["session_id"] = self.session_id
        if self.article is not None:
            data["article"] = self.article.to_dict()
        if self.article_id is not None:
            data["article_id"] = self.article_id
        if self.expected_messages is not None:
            data["expected_messages"] = self.expected_messages
        if self.is_done() or (self.is_input_eof() and self.output is not None):
            data["output"] = self.output
        if self.is_input_eof() and self.input_route is not None:
            data["input_route"] = self.input_route
        if self.query_id is not None:
            data["query_id"] = self.query_id
        if self.is_query_result() or self.type == MsgType.TOP_LOCAL or self.is_word_count():
            data["result"] = self.result
        for name in ("shard_id", "word_count", "url", "partial_sum", "partial_count", "produced_count", "word"):
            value = getattr(self, name)
            if value is not None:
                data[name] = value
        if self.is_avg_ready():
            data["average"] = self.average
        return data
