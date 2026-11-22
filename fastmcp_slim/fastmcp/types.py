"""Reusable type annotations for FastMCP tool parameters.

These types can be used in tool function signatures to influence how
parameters are presented in UIs (e.g. `fastmcp dev apps`) and
serialized in JSON Schema.

Example:

```python
from fastmcp import FastMCP
from fastmcp.types import Textarea

mcp = FastMCP("demo")

@mcp.tool()
def run_query(sql: Textarea) -> str:
    ...
```
"""

from __future__ import annotations

from pydantic import Field
from typing_extensions import Annotated  # noqa: UP035 - Python 3.8

Textarea = Annotated[str, Field(json_schema_extra={"format": "textarea"})]
"""A string rendered as a multiline textarea in form-based UIs.

Produces `"format": "textarea"` in the JSON Schema, which
`fastmcp dev apps` picks up automatically.
"""

__all__ = [
    "Textarea",
]
