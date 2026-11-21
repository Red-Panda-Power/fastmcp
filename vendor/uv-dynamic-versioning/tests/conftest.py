from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from git import Repo, TagReference


@pytest.fixture(scope="session", autouse=True)
def isolated_working_tree(tmp_path_factory):
    original_directory = Path.cwd()
    root = tmp_path_factory.mktemp("versioning-repo")
    shutil.copytree(Path(__file__).parent / "fixtures", root / "tests" / "fixtures")
    shutil.copyfile(
        root / "tests" / "fixtures" / "with-pep440" / "pyproject.toml", root / "pyproject.toml"
    )
    repository = Repo.init(root)
    with repository.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.invalid")
    (root / "tracked.txt").write_text("initial", encoding="utf-8")
    repository.git.add("--all")
    repository.index.commit("Initial test commit")
    os.chdir(root)
    try:
        yield repository
    finally:
        os.chdir(original_directory)


@pytest.fixture(scope="session")
def repo(isolated_working_tree):
    return isolated_working_tree


@pytest.fixture
def semver_tag(repo: Repo):
    tag = repo.create_tag("v1.0.0")
    try:
        yield tag
    finally:
        repo.delete_tag(tag)


@pytest.fixture
def prerelease_tag(repo: Repo):
    tag = repo.create_tag("v1.0.0-alpha1")
    try:
        yield tag
    finally:
        repo.delete_tag(tag)


@pytest.fixture
def dev_tag(repo: Repo):
    tag = repo.create_tag("v1.0.0-dev1")
    try:
        yield tag
    finally:
        repo.delete_tag(tag)


@pytest.fixture
def uv_dynamic_versioning_bypass_with_semver_tag(
    semver_tag: TagReference,
):
    os.environ["UV_DYNAMIC_VERSIONING_BYPASS"] = semver_tag.name

    try:
        yield semver_tag.name
    finally:
        del os.environ["UV_DYNAMIC_VERSIONING_BYPASS"]


@pytest.fixture
def uv_dynamic_versioning_bypass_with_prerelease_tag(prerelease_tag: TagReference):
    os.environ["UV_DYNAMIC_VERSIONING_BYPASS"] = prerelease_tag.name

    try:
        yield prerelease_tag.name
    finally:
        del os.environ["UV_DYNAMIC_VERSIONING_BYPASS"]


@pytest.fixture
def uv_dynamic_versioning_bypass_with_dev_tag(dev_tag: TagReference):
    os.environ["UV_DYNAMIC_VERSIONING_BYPASS"] = dev_tag.name

    try:
        yield dev_tag.name
    finally:
        del os.environ["UV_DYNAMIC_VERSIONING_BYPASS"]
