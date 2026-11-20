"""Compatibility for Pydantic's per-call alias controls on Python 3.8.

Pydantic 2.10 is the last release supporting Python 3.8. Its validators do not
accept the ``by_alias`` and ``by_name`` overrides added in 2.11. Build cached
validators from a private copy of the core schema so wire validation can stay
alias-only without changing model configuration or global Pydantic behavior.
"""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from inspect import signature
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel as PydanticBaseModel
from pydantic import PydanticUserError
from pydantic import TypeAdapter as PydanticTypeAdapter
from pydantic_core import SchemaValidator

_HAS_ALIAS_OVERRIDES = "by_name" in signature(PydanticTypeAdapter.validate_python).parameters
_T = TypeVar("_T")


def _set_validation_options(schema: Any, *, by_alias: bool | None, by_name: bool | None) -> None:
    """Apply overrides throughout copied model and typed-dict schemas."""
    seen: set[int] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if id(value) in seen:
                return
            seen.add(id(value))
            schema_type = value.get("type")
            if (
                isinstance(schema_type, str)
                and schema_type in {"model", "typed-dict", "dataclass"}
                and by_name is not None
            ):
                value.setdefault("config", {})["populate_by_name"] = by_name
            if (
                by_alias is False
                and isinstance(schema_type, str)
                and schema_type in {"model-field", "typed-dict-field", "dataclass-field"}
            ):
                value.pop("validation_alias", None)
            for key, item in value.items():
                if key not in {"metadata", "default", "serialization"}:
                    visit(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                visit(item)

    visit(schema)


@lru_cache(maxsize=512)
def _compiled_validator(owner: Any, schema_id: int, by_alias: bool | None, by_name: bool | None) -> SchemaValidator:
    # schema_id is part of the cache key so an explicit model_rebuild() creates
    # a fresh validator instead of retaining the old schema.
    del schema_id
    schema = owner.core_schema if isinstance(owner, PydanticTypeAdapter) else owner.__pydantic_core_schema__
    schema = deepcopy(schema)
    _set_validation_options(schema, by_alias=by_alias, by_name=by_name)
    return SchemaValidator(schema)


def _validator(owner: Any, *, by_alias: bool | None, by_name: bool | None) -> SchemaValidator:
    if by_alias is False and by_name is not True:
        raise PydanticUserError(
            "At least one of `by_alias` or `by_name` must be set to True.",
            code="validate-by-alias-and-name-false",
        )
    schema = owner.core_schema if isinstance(owner, PydanticTypeAdapter) else owner.__pydantic_core_schema__
    if not isinstance(schema, dict) and isinstance(owner, type) and issubclass(owner, PydanticBaseModel):
        owner.model_rebuild()
        schema = owner.__pydantic_core_schema__
    return _compiled_validator(owner, id(schema), by_alias, by_name)


if TYPE_CHECKING or _HAS_ALIAS_OVERRIDES:
    BaseModel = PydanticBaseModel
    TypeAdapter = PydanticTypeAdapter
else:

    class BaseModel(PydanticBaseModel):
        """Pydantic 2.10 model with per-call alias validation overrides."""

        @classmethod
        def model_validate(
            cls,
            obj: Any,
            *,
            strict: bool | None = None,
            from_attributes: bool | None = None,
            context: Any | None = None,
            by_alias: bool | None = None,
            by_name: bool | None = None,
        ) -> Any:
            if by_alias is None and by_name is None:
                return super().model_validate(obj, strict=strict, from_attributes=from_attributes, context=context)
            validator = _validator(cls, by_alias=by_alias, by_name=by_name)
            return validator.validate_python(obj, strict=strict, from_attributes=from_attributes, context=context)

    class TypeAdapter(PydanticTypeAdapter[_T], Generic[_T]):
        """Pydantic 2.10 adapter with per-call alias validation overrides."""

        def validate_python(
            self,
            object: Any,
            /,
            *,
            strict: bool | None = None,
            from_attributes: bool | None = None,
            context: Any | None = None,
            experimental_allow_partial: Any = False,
            by_alias: bool | None = None,
            by_name: bool | None = None,
        ) -> Any:
            if by_alias is None and by_name is None:
                return super().validate_python(
                    object,
                    strict=strict,
                    from_attributes=from_attributes,
                    context=context,
                    experimental_allow_partial=experimental_allow_partial,
                )
            validator = _validator(self, by_alias=by_alias, by_name=by_name)
            return validator.validate_python(
                object,
                strict=strict,
                from_attributes=from_attributes,
                context=context,
                allow_partial=experimental_allow_partial,
            )

        def validate_json(
            self,
            data: Any,
            /,
            *,
            strict: bool | None = None,
            context: Any | None = None,
            experimental_allow_partial: Any = False,
            by_alias: bool | None = None,
            by_name: bool | None = None,
        ) -> Any:
            if by_alias is None and by_name is None:
                return super().validate_json(
                    data, strict=strict, context=context, experimental_allow_partial=experimental_allow_partial
                )
            validator = _validator(self, by_alias=by_alias, by_name=by_name)
            return validator.validate_json(
                data, strict=strict, context=context, allow_partial=experimental_allow_partial
            )
