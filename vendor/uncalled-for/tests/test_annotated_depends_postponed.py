"""Tests for Annotated dependencies under postponed annotation evaluation."""

from __future__ import annotations

from typing_extensions import Annotated, TypeAliasType

from uncalled_for import (
    Depends,
    Provided,
    get_annotation_dependencies,
    get_dependency_parameters,
    resolved_dependencies,
    without_dependencies,
)


def get_db() -> str:
    return "db"


DB = Annotated[str, Depends(get_db)]


async def get_user(email: str, db: DB) -> str:
    return f"{email} via {db}"


def test_string_annotations_find_annotated_depends() -> None:
    assert set(get_dependency_parameters(get_user)) == {"db"}
    assert get_annotation_dependencies(get_user) == {}


async def test_string_annotations_resolve_annotated_depends() -> None:
    async with resolved_dependencies(get_user, {"email": "a"}) as arguments:
        assert arguments == {"db": "db"}

    assert await without_dependencies(get_user)(email="a") == "a via db"


def get_values() -> list[int]:
    return [1, 2]


async def modern_annotation(value: Annotated[list[int] | None, Depends(get_values)]) -> int:
    return sum(value or [])


async def test_modern_postponed_annotation_resolves_dependency() -> None:
    assert set(get_dependency_parameters(modern_annotation)) == {"value"}
    assert await without_dependencies(modern_annotation)() == 3


CompatDB = TypeAliasType("CompatDB", Annotated[str, Depends(get_db)])


async def aliased_annotation(db: CompatDB = Provided) -> str:
    return db


async def test_backported_type_alias_preserves_dependency_metadata() -> None:
    assert await without_dependencies(aliased_annotation)() == "db"
