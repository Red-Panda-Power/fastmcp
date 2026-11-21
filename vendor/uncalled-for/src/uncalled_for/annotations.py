"""Annotation-based dependency extraction from ``Annotated`` type hints."""

from __future__ import annotations

import inspect
import sys
from collections.abc import Callable
from typing import Any, ForwardRef, cast

from typing_extensions import Annotated, TypeAliasType, get_args, get_origin, get_type_hints

from .base import Dependency, Provider

if sys.version_info >= (3, 12):
    from typing import TypeAliasType as _NativeTypeAliasType

    _ALIAS_TYPES = (TypeAliasType, _NativeTypeAliasType)
else:
    _ALIAS_TYPES = (TypeAliasType,)


def _get_type_hints(function: Callable[..., object]) -> dict[str, Any]:
    """Resolve postponed modern annotations on interpreters before Python 3.10."""
    if sys.version_info >= (3, 10):
        return get_type_hints(function, include_extras=True)

    from eval_type_backport import eval_type_backport

    if getattr(function, "__no_type_check__", False):
        return {}
    target = inspect.unwrap(function)
    namespace = getattr(target, "__globals__", {})
    hints = {}
    for name, annotation in getattr(function, "__annotations__", {}).items():
        if annotation is None:
            annotation = type(None)
        elif isinstance(annotation, str):
            annotation = ForwardRef(annotation)
        resolved = eval_type_backport(annotation, globalns=namespace, localns=namespace)
        if isinstance(resolved, ForwardRef):
            resolved = eval_type_backport(resolved, globalns=namespace, localns=namespace)
        hints[name] = resolved
    return hints


def _metadata(hint: object) -> tuple[object, ...]:
    """Collect the ``Annotated`` metadata of a hint, through ``type`` aliases.

    ``type DB = Annotated[Connection, Depends(get_db)]`` hides its metadata
    behind the alias, and ``Annotated[DB, Traced()]`` does not merge the two
    the way nested ``Annotated`` forms do, so both have to be unwrapped here.
    The alias's metadata comes first, like the inner form of a nested
    ``Annotated``.
    """
    if isinstance(hint, _ALIAS_TYPES):
        return _metadata(hint.__value__)
    origin = get_origin(hint)
    if isinstance(origin, _ALIAS_TYPES):
        return _metadata(origin.__value__)
    if origin is Annotated:
        base, *metadata = get_args(hint)
        return (*_metadata(base), *metadata)
    return ()


_metadata_cache: dict[Callable[..., object], dict[str, list[Dependency[object]]]] = {}
_annotation_cache: dict[Callable[..., object], dict[str, list[Dependency[object]]]] = {}


def _metadata_dependencies(
    function: Callable[..., object],
) -> dict[str, list[Dependency[object]]]:
    """Find the dependencies in each parameter's ``Annotated`` metadata."""
    if function in _metadata_cache:
        return _metadata_cache[function]

    result: dict[str, list[Dependency[object]]] = {}
    try:
        hints = _get_type_hints(function)
    except Exception:
        _metadata_cache[function] = result
        return result

    for name, hint in hints.items():
        if name == "return":
            continue
        dependencies: list[Dependency[object]] = []
        for a in _metadata(hint):
            if isinstance(a, Dependency):
                dependencies.append(cast(Dependency[object], a))
            elif isinstance(a, type) and issubclass(a, Dependency):
                dependencies.append(cast(Dependency[object], a()))
        if dependencies:
            result[name] = dependencies

    _metadata_cache[function] = result
    return result


def get_annotation_dependencies(
    function: Callable[..., object],
) -> dict[str, list[Dependency[object]]]:
    """Find ``Dependency`` instances in ``Annotated`` type-hint metadata.

    Bare ``Dependency`` subclasses are also accepted as a shorthand for a
    parameterless instance: ``Annotated[T, Dep]`` is equivalent to
    ``Annotated[T, Dep()]``.

    These dependencies wrap the call but do not supply the parameter's value.
    ``Provider`` metadata, such as ``Depends(...)``, does supply the value, so
    it is reported by ``get_dependency_parameters`` instead.
    """
    if function in _annotation_cache:
        return _annotation_cache[function]

    result: dict[str, list[Dependency[object]]] = {}
    for name, dependencies in _metadata_dependencies(function).items():
        side_effects = [d for d in dependencies if not isinstance(d, Provider)]
        if side_effects:
            result[name] = side_effects

    _annotation_cache[function] = result
    return result
