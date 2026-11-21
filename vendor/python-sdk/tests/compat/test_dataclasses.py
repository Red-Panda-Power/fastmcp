"""Compatibility checks for the SDK's Python 3.8 dataclass backport."""

from __future__ import annotations

import dataclasses
import importlib.util
import inspect
from pathlib import Path

import pytest

compat_path = Path(__file__).parents[2] / "mcp" / "mcp" / "shared" / "_dataclasses.py"
spec = importlib.util.spec_from_file_location("mcp_dataclasses_compat", compat_path)
assert spec is not None and spec.loader is not None
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)
dataclass = compat.dataclass
KW_ONLY = compat.KW_ONLY


def test_keyword_only_marker_preserves_generated_dataclass_behavior():
    @dataclass
    class Request:
        name: str
        _: KW_ONLY
        values: list[int] = dataclasses.field(default_factory=list)
        ready: bool = dataclasses.field(init=False, default=False)

        def __post_init__(self):
            self.ready = True

    request = Request("one", values=[2])
    assert request.ready and request.values == [2]
    assert Request("other").values is not Request("third").values
    assert [field.name for field in dataclasses.fields(Request)] == ["name", "values", "ready"]
    assert inspect.signature(Request).parameters["values"].kind is inspect.Parameter.KEYWORD_ONLY
    assert dataclasses.replace(request, name="changed").values == [2]
    with pytest.raises(TypeError):
        Request("one", [2])


def test_keyword_only_frozen_dataclass():
    @dataclass(frozen=True, kw_only=True)
    class Context:
        name: str
        enabled: bool = True

    context = Context(name="mcp")
    assert dataclasses.replace(context, enabled=False) == Context(name="mcp", enabled=False)
    with pytest.raises(TypeError):
        Context("mcp")
    with pytest.raises(dataclasses.FrozenInstanceError):
        context.name = "other"


@pytest.mark.parametrize("frozen", [False, True])
def test_slots_keep_stdlib_dataclass_fields(frozen):
    @dataclass(slots=True, frozen=frozen)
    class Entry:
        key: str
        value: int = 3

    entry = Entry("one")
    assert entry.value == 3
    assert not hasattr(entry, "__dict__")
    assert [field.name for field in dataclasses.fields(entry)] == ["key", "value"]
    assert dataclasses.replace(entry, value=7) == Entry("one", 7)
    if frozen:
        with pytest.raises(dataclasses.FrozenInstanceError):
            entry.value = 8
