"""Transport protocol for MCP clients."""

from __future__ import annotations

from typing import AsyncContextManager, Protocol, Tuple, Union

from mcp.shared._stream_protocols import ReadStream, WriteStream
from mcp.shared.message import SessionMessage

__all__ = ["ReadStream", "WriteStream", "Transport", "TransportStreams"]

TransportStreams = Tuple[ReadStream[Union[SessionMessage, Exception]], WriteStream[SessionMessage]]


class Transport(AsyncContextManager[TransportStreams], Protocol):
    """Protocol for MCP transports.

    A transport is an async context manager that yields read and write streams
    for bidirectional communication with an MCP server.
    """
