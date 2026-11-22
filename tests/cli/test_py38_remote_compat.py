"""FastMCP remote bridge configuration on Python 3.8."""

import pytest

from fastmcp.client.transports import StreamableHttpTransport
from fastmcp_remote.cli import build_transport, parse_args


def test_remote_arguments_create_http_transport():
    config = parse_args(
        ["https://example.com/mcp", "--auth", "none", "--header", "X-Client: internal"]
    )
    transport = build_transport(config)
    assert isinstance(transport, StreamableHttpTransport)
    assert config.headers == {"X-Client": "internal"}
    assert config.verify is None


def test_remote_arguments_reject_non_http_url():
    with pytest.raises(SystemExit):
        parse_args(["file:///tmp/server"])
