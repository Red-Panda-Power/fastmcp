"""Python 3.8-compatible regression coverage for Skills runtime imports."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from fastmcp.skills import Skill, SkillFrontmatter, SkillResource
from fastmcp.skills.provider import SkillsDirectoryProvider


def test_frontmatter_validates_and_preserves_json_values() -> None:
    frontmatter = SkillFrontmatter.model_validate(
        {
            "name": "review",
            "description": "Review a change",
            "metadata": {"priority": 1},
        }
    )

    assert frontmatter.name == "review"
    assert frontmatter.model_dump()["metadata"] == {"priority": 1}

    with pytest.raises(ValidationError, match="name must be"):
        SkillFrontmatter.model_validate({"name": "Review", "description": "x"})


def test_skill_directory_provider_loads_and_rejects_invalid_folder(
    tmp_path: Path,
) -> None:
    root = tmp_path / "skills"
    skill_root = root / "review"
    skill_root.mkdir(parents=True)
    (skill_root / "SKILL.md").write_text(
        "---\nname: review\ndescription: Review a change\n---\n# Review\n"
    )
    (skill_root / "reference.md").write_bytes(b"Use the diff.\n")

    provider = SkillsDirectoryProvider(root)
    skill = provider._static["review"]

    assert skill.files["reference.md"] == b"Use the diff.\n"
    assert skill.to_mcp_skill().uri == "skill://review/SKILL.md"

    invalid = root / "invalid"
    invalid.mkdir()
    (invalid / "SKILL.md").write_text("---\nname: Wrong\ndescription: invalid\n---\n")
    with pytest.raises(ValueError, match="not valid Agent Skills"):
        SkillsDirectoryProvider(root)


def test_skill_package_and_resource_validation(tmp_path: Path, monkeypatch) -> None:
    package = tmp_path / "py38_skillpkg"
    folder = package / "skills" / "review"
    folder.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (folder / "SKILL.md").write_text(
        "---\nname: review\ndescription: Review a change\n---\n# Review\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    assert Skill.from_package("py38_skillpkg", "skills/review").name == "review"
    with pytest.raises(ValidationError, match="non-negative integer"):
        SkillResource.model_validate(
            {
                "uri": "skill://review/SKILL.md",
                "digest": "sha256:" + "a" * 64,
                "size": True,
            }
        )
