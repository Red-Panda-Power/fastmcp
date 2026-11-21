# Python 3.8 backport of pydocket

This directory is the Python package from `pydocket` 0.29.1, upstream commit
`a25a6d29f0551d25a56b06de44cdfc4ceca2653a` (`python/v0.29.1`) in
<https://github.com/chrisguidry/docket>. It is licensed under MIT; the
upstream `LICENSE` is retained.

The local `+py38` build backports the runtime paths exercised by the included
Python 3.8 checks while replacing Python 3.11-only primitives with maintained
backports where required. It is intended to be selected by the root project's
uv source configuration.

Validation does not establish that every upstream integration is operational
on Python 3.8. The in-memory worker paths cover scheduling, cancellation,
lifecycle, progress, results, exceptions, and dependency injection. No real
Redis instance was available to validate Redis ACL credential rotation or token
refresh. In addition, three queued-cancellation upstream tests run their test
bodies successfully but report teardown errors under Python 3.8 because
pytest-asyncio 0.24 finalizes async-generator fixtures in a different
`ContextVar` context.
