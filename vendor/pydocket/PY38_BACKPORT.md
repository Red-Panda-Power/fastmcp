# Python 3.8 backport of pydocket

This directory is the Python package from `pydocket` 0.29.1, upstream commit
`a25a6d29f0551d25a56b06de44cdfc4ceca2653a` (`python/v0.29.1`) in
<https://github.com/chrisguidry/docket>. It is licensed under MIT; the
upstream `LICENSE` is retained.

The local `+py38` build preserves the 0.29.1 feature set while replacing
Python 3.11-only runtime primitives with maintained backports where required.
It is intended to be selected by the root project's uv source configuration.
