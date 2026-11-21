"""Keyword-only dataclasses for the Python 3.8 compatibility port."""

from __future__ import annotations

import dataclasses
import inspect
import sys
from typing import Any, TypeVar

from key_value._typing_compat import runtime_typing as _py38_typing

T = TypeVar("T")


def keyword_only_dataclass(cls: _py38_typing.Type[T]) -> _py38_typing.Type[T]:
    """Decorate the storage library's simple keyword-only dataclasses."""
    if sys.version_info >= (3, 10):
        return dataclasses.dataclass(cls, kw_only=True)

    cls = dataclasses.dataclass(cls, init=False)
    all_fields = dataclasses.fields(cls)
    fields = tuple(field for field in all_fields if field.init)
    factory_default = object()
    parameters = [inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    for field in fields:
        if field.default is not dataclasses.MISSING:
            default = field.default
        elif field.default_factory is not dataclasses.MISSING:
            default = factory_default
        else:
            default = inspect.Parameter.empty
        parameters.append(inspect.Parameter(field.name, inspect.Parameter.KEYWORD_ONLY, default=default, annotation=field.type))
    signature = inspect.Signature(parameters)

    def init(self: Any, **kwargs: Any) -> None:
        arguments = signature.bind(self, **kwargs)
        arguments.apply_defaults()
        for field in fields:
            value = arguments.arguments[field.name]
            if value is factory_default:
                value = field.default_factory()
            setattr(self, field.name, value)
        for field in all_fields:
            if not field.init and field.default_factory is not dataclasses.MISSING:
                setattr(self, field.name, field.default_factory())
        post_init = getattr(self, "__post_init__", None)
        if post_init is not None:
            post_init()

    init.__signature__ = signature
    init.__qualname__ = cls.__qualname__ + ".__init__"
    cls.__init__ = init
    return cls
