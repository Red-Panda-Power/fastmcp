"""Verify that UV can load the local build plugin in an isolated build."""

from email.parser import Parser
import os
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile

import pytest


def test_uv_build_renders_dynamic_metadata(tmp_path: Path) -> None:
    uvx = shutil.which("uvx")
    if uvx is None:
        pytest.skip("uvx is required for the isolated UV build")

    source = Path(__file__).resolve().parents[1].as_posix()
    package = tmp_path / "build_fixture"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        f"""
[project]
name = "build-fixture"
dynamic = ["version", "dependencies", "optional-dependencies"]
requires-python = ">=3.8"

[build-system]
requires = ["hatchling", "uv-dynamic-versioning>=0.7.0"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "uv-dynamic-versioning"

[tool.hatch.metadata.hooks.uv-dynamic-versioning]
dependencies = ["packaging>=21"]

[tool.hatch.metadata.hooks.uv-dynamic-versioning.optional-dependencies]
feature = ["six=={{{{ version }}}}"]

[tool.uv-dynamic-versioning]
style = "pep440"
fallback-version = "0.0.0"

[tool.uv.sources]
uv-dynamic-versioning = {{ path = "{source}" }}
""",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["UV_DYNAMIC_VERSIONING_BYPASS"] = "1.2.3"
    subprocess.run(
        [uvx, "uv@0.13.9", "build", "--wheel", "--python", sys.executable],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    wheel = next((tmp_path / "dist").glob("*.whl"))
    with ZipFile(wheel) as archive:
        metadata_file = next(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = Parser().parsestr(archive.read(metadata_file).decode("utf-8"))
    assert metadata["Version"] == "1.2.3"
    assert "packaging>=21" in metadata.get_all("Requires-Dist")
    assert "six==1.2.3; extra == 'feature'" in metadata.get_all("Requires-Dist")
