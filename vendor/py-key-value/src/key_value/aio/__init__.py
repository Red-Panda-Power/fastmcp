import os
import sys
from pathlib import Path
from typing import Any, BinaryIO, Iterable

from beartype import (
    BeartypeConf,
    BeartypeStrategy,
)
from beartype.claw import beartype_this_package


class _Py38ResourceReader:
    """Expose filesystem resources for loaders wrapped by beartype on Python 3.8."""

    def __init__(self, loader_path: str) -> None:
        self._package_path = Path(loader_path).parent

    def open_resource(self, resource: str) -> BinaryIO:
        return (self._package_path / resource).open("rb")

    def resource_path(self, resource: str) -> str:
        return str(self._package_path / resource)

    def is_resource(self, resource: str) -> bool:
        return (self._package_path / resource).is_file()

    def contents(self) -> Iterable[str]:
        return (path.name for path in self._package_path.iterdir())

    def files(self) -> Path:
        return self._package_path


def _patch_beartype_resource_reader() -> None:
    """Keep beartype's import hook compatible with ``importlib_resources`` on 3.8.

    ``beartype_this_package`` uses a source loader for every Python module it
    encounters. On Python 3.8, ``importlib_resources`` cannot recognize that
    subclass as the standard filesystem loader and falls back to a non-recursive
    reader. Packages with nested resources, including ``jsonschema_specifications``,
    then appear empty. Supplying a reader with ``files()`` preserves the import
    hook and its runtime checks while restoring normal resource traversal.
    """
    if sys.version_info >= (3, 9):
        return

    from beartype.claw._importlib._clawimpload import BeartypeSourceFileLoader

    if getattr(BeartypeSourceFileLoader, "_key_value_py38_reader", False):
        return

    original_get_resource_reader = BeartypeSourceFileLoader.get_resource_reader

    def get_resource_reader(loader: Any, fullname: str) -> Any:
        loader_path = Path(loader.path)
        if loader_path.name == "__init__.py":
            return _Py38ResourceReader(str(loader_path))
        return original_get_resource_reader(loader, fullname)

    BeartypeSourceFileLoader.get_resource_reader = get_resource_reader
    BeartypeSourceFileLoader._key_value_py38_reader = True


disable_beartype = os.environ.get("PY_KEY_VALUE_DISABLE_BEARTYPE", "false").lower() in ("true", "1", "yes")

strategy = BeartypeStrategy.O0 if disable_beartype else BeartypeStrategy.O1

_patch_beartype_resource_reader()
beartype_this_package(conf=BeartypeConf(violation_type=UserWarning, strategy=strategy))
