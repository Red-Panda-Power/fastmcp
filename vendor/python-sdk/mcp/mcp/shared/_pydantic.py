"""Pydantic validation helpers for the Python 3.8 dependency set."""

from __future__ import annotations

import sys
from typing import Any

if sys.version_info < (3, 9):
    from mcp_types._pydantic_compat import _validator
    from mcp_types._pydantic_compat import TypeAdapter as TypeAdapter
else:
    from pydantic import TypeAdapter as TypeAdapter


def validate_model(model: Any, value: Any, *, by_name: bool | None = None, by_alias: bool | None = None) -> Any:
    if sys.version_info < (3, 9):
        if by_name is None and by_alias is None:
            return model.model_validate(value)
        return _validator(model, by_name=by_name, by_alias=by_alias).validate_python(value)
    return model.model_validate(value, by_name=by_name, by_alias=by_alias)


def validate_adapter(adapter: Any, value: Any, *, by_name: bool | None = None, by_alias: bool | None = None) -> Any:
    if sys.version_info < (3, 9):
        if by_name is None and by_alias is None:
            return adapter.validate_python(value)
        return _validator(adapter, by_name=by_name, by_alias=by_alias).validate_python(value)
    return adapter.validate_python(value, by_name=by_name, by_alias=by_alias)
