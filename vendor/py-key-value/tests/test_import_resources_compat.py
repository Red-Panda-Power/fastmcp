"""Regression coverage for beartype's Python 3.8 import hook."""

import subprocess
import sys


def test_beartype_import_hook_preserves_nested_package_resources():
    script = """
import key_value.aio
import jsonschema
from jsonschema_specifications import REGISTRY
from key_value.aio._utils.time_to_live import seconds_to

assert 'http://json-schema.org/draft-03/schema' in REGISTRY
assert 'http://json-schema.org/draft-04/schema' in REGISTRY
assert hasattr(seconds_to, '__beartype_wrapper')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
