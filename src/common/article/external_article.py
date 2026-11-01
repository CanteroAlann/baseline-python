import ast
from dataclasses import dataclass
from datetime import datetime
import json
from typing import Any, Self

from .article import Article
from .clean_article import CleanArticle

COLUMNS_TO_DROP = [
    "additional_entities", "date_created", "description", "event", "identifier",
    "infoboxes", "is_part_of", "license", "main_entity", "references", "tables", "version",
]


def in_language_parse(value: Any) -> Any:
    if not isinstance(value, dict):
        return None
    return value.get("identifier", None)


def image_object_to_url(image: Any) -> Any:
    if not isinstance(image, dict):
        return None
    return image.get("content_url", None)


def parse_field(value: Any, default: Any = None) -> Any:
    if not isinstance(value, str):
        return value
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return ast.literal_eval(value)


def has_biography_section(sections: list[dict[str, Any]]) -> bool:
    for section in sections:
        name = section.get("name", "")
        if section.get("type") == "section" and name.lower() in ("biography", "biographie"):
            return True
        if has_biography_section(section.get("has_parts", [])):
            return True
    return False


@dataclass
class ExternalArticle(Article):
    data: dict[str, Any]

    @property
    def name(self) -> str:
        return self.data["name"]

    @property
    def url(self) -> str:
        return self.data.get("url", "")

    @property
    def date_modified(self) -> str | None:
        return self.data.get("date_modified") or None

    @property
    def date_modified_year(self) -> int | None:
        modified = self.data.get("date_modified") or None
        return datetime.fromisoformat(modified).year if modified else None

    @property
    def in_language(self) -> str | None:
        return in_language_parse(parse_field(self.data.get("in_language")))

    @property
    def image_url(self) -> str | None:
        """Extrae la URL de la imagen de forma limpia."""
        image = parse_field(self.data.get("image"))
        return image_object_to_url(image)

    @property
    def has_biography(self) -> bool:
        """Determina si el artículo tiene la sección biography o biographie."""
        sections = parse_field(self.data.get("sections"), [])
        if not isinstance(sections, list):
            return False
        return has_biography_section(sections)

    def to_dict(self) -> dict[str, Any]:
        return self.data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(data)

    def to_clean_article(self, abstract_words: list[str]) -> CleanArticle:
        fields = {key: value for key, value in self.data.items() if key not in COLUMNS_TO_DROP}
        sections = parse_field(fields.get("sections", ""), [])
        modified = fields.get("date_modified")
        unique_words = set(abstract_words)
        return CleanArticle(
            abstract=unique_words,
            date_modified=datetime.fromisoformat(modified).isoformat(sep=" ") if modified else None,
            image=image_object_to_url(parse_field(fields.get("image"))),
            in_language=in_language_parse(parse_field(fields.get("in_language"))),
            name=fields["name"],
            has_bio=has_biography_section(sections),
            url=fields.get("url", ""),
        )
