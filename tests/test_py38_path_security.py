"""Filesystem and multi-provider authorization safety on Python 3.8."""

import pytest
from mcp.shared.path_security import PathEscapeError, safe_join

from fastmcp.server.auth import MultiAuth
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.providers.skills._common import resolve_within
from fastmcp.utilities.paths import is_relative_to


def test_containment_checks_reject_paths_outside_the_root(tmp_path):
    root = tmp_path.resolve()
    child = safe_join(root, "nested", "file.txt")
    assert is_relative_to(child, root)
    assert resolve_within(root, "nested/file.txt") == child
    assert not is_relative_to(root.parent / "outside", root)

    with pytest.raises(PathEscapeError):
        safe_join(root, "../outside")
    with pytest.raises(PathEscapeError):
        resolve_within(root, "../outside")


def test_containment_checks_reject_symlink_escapes(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    link = root / "escape"
    try:
        link.symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip("creating symlinks requires operating system permission")
    with pytest.raises(PathEscapeError):
        safe_join(root, "escape/outside.txt")


@pytest.mark.asyncio
async def test_multiple_authentication_sources_keep_identity_and_length_checks():
    verifier = StaticTokenVerifier({"valid": {"client_id": "client"}})
    auth = MultiAuth(verifiers={"trusted": verifier})
    result = await auth.verify_token("valid")
    assert result is not None
    assert result.original_client_id == "client"
    assert await auth.verify_token("invalid") is None

    auth._source_ids.append("unexpected")
    with pytest.raises(ValueError, match="equal lengths"):
        await auth.verify_token("valid")
