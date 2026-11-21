# Vendored pytest-retry

These sources and tests come from [str0zzapreti/pytest-retry](https://github.com/str0zzapreti/pytest-retry), tag `1.7.0`, commit `e576326b9be7b935aca9374c8f4df3d09d573dde`. The original MIT license and README are preserved in `LICENSE` and `UPSTREAM-README.md`.

This copy backports the pytest plugin to Python 3.8 so development tests can retain their retry behavior. The root UV configuration selects it for Python 3.8, and the temporary bootstrap project installs it with its development tools. It is not a runtime dependency.
