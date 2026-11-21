"""Beartype configuration and decorators for runtime type checking.

This module provides decorators for controlling beartype's runtime type checking
behavior. Use `bear_enforce` when you want type violations to raise exceptions
rather than warnings.
"""

from __future__ import annotations

from key_value._typing_compat import runtime_typing as _py38_typing


from beartype import BeartypeConf, BeartypeStrategy, beartype
from typing_extensions import ParamSpec, TypeVar

no_bear_type_check_conf = BeartypeConf(strategy=BeartypeStrategy.O0)

no_bear_type = beartype(conf=no_bear_type_check_conf)

enforce_bear_type_conf = BeartypeConf(strategy=BeartypeStrategy.O1, violation_type=TypeError)
enforce_bear_type = beartype(conf=enforce_bear_type_conf)

P = ParamSpec(name="P")
R = TypeVar(name="R")


def no_bear_type_check(func: _py38_typing.Callable[P, R]) -> _py38_typing.Callable[P, R]:
    """Disable beartype checking for a function."""
    return no_bear_type(func)


def bear_enforce(func: _py38_typing.Callable[P, R]) -> _py38_typing.Callable[P, R]:
    """Enforce beartype with exceptions instead of warnings."""
    return enforce_bear_type(func)


# Legacy alias
bear_spray = no_bear_type_check
