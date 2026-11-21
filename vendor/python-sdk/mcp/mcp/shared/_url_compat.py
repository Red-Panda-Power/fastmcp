"""Preserve an empty URL path with Pydantic 2.10 on Python 3.8.

The newer Pydantic ``url_preserve_empty_path`` option is essential for OAuth
issuer comparisons, where ``https://example.com`` and the same URL ending in
``/`` are different identifiers.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl as _PydanticAnyHttpUrl
from pydantic import AnyUrl as _PydanticAnyUrl
from pydantic import TypeAdapter
from pydantic_core import core_schema


def _remove_added_slash(value: str) -> str:
    authority_start = value.find("://")
    if authority_start < 0:
        return value
    authority_start += 3
    positions = [position for char in "/?#" if (position := value.find(char, authority_start)) >= 0]
    if not positions:
        return value
    path_start = min(positions)
    if value[path_start] == "/" and (path_start + 1 == len(value) or value[path_start + 1] in "?#"):
        return value[:path_start] + value[path_start + 1 :]
    return value


class _PreserveEmptyPath:
    def __init__(self, url: Any) -> None:
        validated = TypeAdapter(self.__class__).validate_python(url)
        self._url = validated._url
        self._empty_path = validated._empty_path

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any:
        schema = super().__get_pydantic_core_schema__(source_type, handler)

        def preserve(value: Any, validate: Any) -> Any:
            result = validate(value)
            if isinstance(value, _PreserveEmptyPath):
                result._empty_path = value._empty_path
            else:
                raw = value.decode() if isinstance(value, bytes) else str(value)
                result._empty_path = urlsplit(raw).path == ""
            return result

        return core_schema.no_info_wrap_validator_function(preserve, schema)

    @property
    def path(self) -> str | None:
        return None if self._empty_path else super().path

    def __str__(self) -> str:
        value = super().__str__()
        return _remove_added_slash(value) if self._empty_path else value

    def unicode_string(self) -> str:
        value = super().unicode_string()
        return _remove_added_slash(value) if self._empty_path else value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self)!r})"

    def __deepcopy__(self, memo: dict[str, Any]) -> Any:
        return self.__class__(self)

    def __eq__(self, other: Any) -> bool:
        matching_base = (self.__class__ is AnyUrl and other.__class__ is _PydanticAnyUrl) or (
            self.__class__ is AnyHttpUrl and other.__class__ is _PydanticAnyHttpUrl
        )
        return (self.__class__ is other.__class__ or matching_base) and str(self) == str(other)

    def __hash__(self) -> int:
        return hash(self._url)

    @classmethod
    def serialize_url(cls, value: Any, info: Any) -> Any:
        if isinstance(value, _PydanticAnyUrl):
            return str(value) if info.mode == "json" else value
        return super().serialize_url(value, info)


class AnyUrl(_PreserveEmptyPath, _PydanticAnyUrl):
    pass


class AnyHttpUrl(_PreserveEmptyPath, _PydanticAnyHttpUrl):
    pass
