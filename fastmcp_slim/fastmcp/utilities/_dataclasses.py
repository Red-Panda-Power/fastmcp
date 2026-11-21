"""Dataclass compatibility adapted from the vendored MCP SDK."""

from __future__ import annotations

import dataclasses
import functools
import inspect
import sys
from typing import Any, Callable, TypeVar  # noqa: UP035 - Python 3.8

T = TypeVar("T", bound=type)

if sys.version_info >= (3, 10):  # noqa: UP036 - Python 3.8 compatibility
    from dataclasses import KW_ONLY, dataclass
else:

    class _KeywordOnly:
        pass

    KW_ONLY = _KeywordOnly()

    def _add_slots(cls: T, frozen: bool) -> T:
        """Create slots after dataclass processing, as the standard library does."""
        if "__slots__" in cls.__dict__:
            raise TypeError(f"{cls.__name__} already specifies __slots__")

        namespace = dict(cls.__dict__)
        names = tuple(field.name for field in dataclasses.fields(cls))
        namespace["__slots__"] = names
        for name in names:
            namespace.pop(name, None)
        namespace.pop("__dict__", None)
        namespace.pop("__weakref__", None)
        result = type(cls)(cls.__name__, cls.__bases__, namespace)
        result.__qualname__ = cls.__qualname__

        if frozen:
            if "__getstate__" not in namespace:
                result.__getstate__ = _dataclass_getstate
            if "__setstate__" not in namespace:
                result.__setstate__ = _dataclass_setstate
        return result

    def _dataclass_getstate(self: Any) -> list[Any]:
        return [getattr(self, field.name) for field in dataclasses.fields(self)]

    def _dataclass_setstate(self: Any, state: list[Any]) -> None:
        for field, value in zip(dataclasses.fields(self), state):  # noqa: B905 - Python 3.8
            object.__setattr__(self, field.name, value)

    def _keyword_only_init(cls: T, names: set[str]) -> None:
        """Enforce keyword-only fields while retaining the stdlib-generated init."""
        original = cls.__init__
        signature = inspect.signature(original)
        parameters = list(signature.parameters.values())
        positional = [
            parameter for parameter in parameters if parameter.name not in names
        ]
        keyword_only = [
            parameter.replace(kind=inspect.Parameter.KEYWORD_ONLY)
            for parameter in parameters
            if parameter.name in names
        ]
        signature = signature.replace(parameters=[*positional, *keyword_only])

        @functools.wraps(original)
        def init(self: Any, *args: Any, **kwargs: Any) -> None:
            arguments = signature.bind(self, *args, **kwargs).arguments
            arguments.pop(parameters[0].name)
            original(self, **arguments)

        init.__signature__ = signature
        cls.__init__ = init

    def dataclass(cls: T | None = None, **options: Any) -> T | Callable[[T], T]:
        slots = options.pop("slots", False)
        kw_only = options.pop("kw_only", False)
        # Python 3.8 has no pattern matching; accept the 3.10 option so shared
        # declarations can be used unchanged.
        options.pop("match_args", True)

        def decorate(target: T) -> T:
            original_annotations = target.__dict__.get("__annotations__", {})
            annotations = dict(original_annotations)
            keyword_names = set()
            for base in target.__mro__[1:]:
                keyword_names.update(
                    getattr(base, "__fastmcp_keyword_only_fields__", ())
                )
            keyword_names.difference_update(annotations)
            marker = None
            for name, annotation in annotations.items():
                if annotation is KW_ONLY or annotation == "KW_ONLY":
                    if marker is not None:
                        raise TypeError("more than one KW_ONLY marker")
                    marker = name
                elif marker is not None or kw_only:
                    keyword_names.add(name)

            if marker is not None:
                del annotations[marker]
                target.__annotations__ = annotations

            had_init = "__init__" in target.__dict__
            result = dataclasses.dataclass(target, **options)
            if marker is not None:
                result.__annotations__ = original_annotations
            result.__fastmcp_keyword_only_fields__ = frozenset(keyword_names)
            if keyword_names and options.get("init", True) and not had_init:
                _keyword_only_init(result, keyword_names)
            if slots:
                result = _add_slots(result, options.get("frozen", False))
            return result

        return decorate(cls) if cls is not None else decorate
