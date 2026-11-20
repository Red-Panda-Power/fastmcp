"""Shared pydantic base for the generated `mcp_types._v*` wire-shape packages."""

from pydantic import ConfigDict

from mcp_types._pydantic_compat import BaseModel


class WireModel(BaseModel):
    """Base for generated wire models: enables `populate_by_name`; subclasses set `extra` themselves."""

    model_config = ConfigDict(populate_by_name=True)
