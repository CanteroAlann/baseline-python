from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from .article import Article


@dataclass
class CleanArticle(Article):
    abstract: set[str]
    date_modified: str | None
    image: str | None
    in_language: str | None
    name: str
    has_bio: bool
    url: str

    @property
    def abstract_word_count(self) -> int:
        return len(self.abstract)

    @property
    def date_modified_year(self) -> int | None:
        if self.date_modified is None:
            return None
        return datetime.fromisoformat(self.date_modified).year

    def to_dict(self) -> dict[str, Any]:
        return {
            "abstract": sorted(self.abstract),
            "abstract_word_count": self.abstract_word_count,
            "date_modified": self.date_modified,
            "image": self.image,
            "in_language": self.in_language,
            "name": self.name,
            "has_bio": self.has_bio,
            "url": self.url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        fields = data.copy()
        fields.pop("abstract_word_count")
        fields["abstract"] = set(fields["abstract"])
        return cls(**fields)
