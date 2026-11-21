"""Base exception classes for key-value store errors."""

from __future__ import annotations

from key_value._typing_compat import runtime_typing as _py38_typing

ExtraInfoType = _py38_typing.Dict[str, _py38_typing.Union[str, int, float, bool, None]]


class BaseKeyValueError(Exception):
    """Base exception for all KV Store Adapter errors."""

    extra_info: _py38_typing.Union[ExtraInfoType, None] = None
    message: _py38_typing.Union[str, None] = None

    def __init__(self, message: _py38_typing.Union[str, None] = None, extra_info: _py38_typing.Union[ExtraInfoType, None] = None):
        message_parts: _py38_typing.List[str] = []

        if message:
            message_parts.append(message)

        if extra_info:
            extra_info_str = ";".join(f"{k}: {v}" for k, v in extra_info.items())
            if message:
                extra_info_str = "(" + extra_info_str + ")"

            message_parts.append(extra_info_str)

        self.message = ": ".join(message_parts)

        super().__init__(self.message)

        self.extra_info = extra_info
