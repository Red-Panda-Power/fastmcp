from __future__ import annotations

import compileall
import sys
from pathlib import Path
from typing import Any, Dict

try:
    import tomllib
except ImportError:
    import tomli as tomllib


PROJECT_ROOT = Path(__file__).parents[3]
STORES_ROOT = PROJECT_ROOT / "src" / "key_value" / "aio" / "stores"


def _optional_dependencies() -> Dict[str, Any]:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as pyproject:
        project = tomllib.load(pyproject)
    return project["project"]["optional-dependencies"]


def test_all_vendored_backends_have_declared_extras_or_are_stdlib() -> None:
    extras = _optional_dependencies()
    expected_extras = {
        "aerospike",
        "azure-tables",
        "chdb",
        "disk",
        "duckdb",
        "dynamodb",
        "elasticsearch",
        "filetree",
        "firestore",
        "keyring",
        "memcached",
        "memory",
        "mongodb",
        "opensearch",
        "postgresql",
        "redis",
        "rocksdb",
        "s3",
        "valkey",
        "vault",
    }
    store_names = {path.name for path in STORES_ROOT.iterdir() if path.is_dir()}

    assert expected_extras <= extras.keys()
    assert {"null", "simple", "windows_registry"} <= store_names
    assert extras["registry"] == []


def test_unsupported_py38_backends_are_explicitly_marked() -> None:
    extras = _optional_dependencies()

    assert extras["chdb"] == ["chdb>=4.1.1; python_version >= '3.9'"]
    assert extras["valkey"] == ["valkey-glide>=2.1.0; python_version >= '3.9'"]


def test_store_sources_parse_on_the_running_python() -> None:
    assert sys.version_info >= (3, 8)
    assert compileall.compile_dir(str(STORES_ROOT), quiet=1)
