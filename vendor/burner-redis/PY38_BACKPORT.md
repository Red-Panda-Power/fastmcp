# Python 3.8 backport of burner-redis

This directory is `burner-redis` 0.1.7, upstream commit
`5191d4e59a62918c7906c357f95e179ab9d921c3` (`v0.1.7`) from
<https://github.com/PrefectHQ/burner-redis>. It is licensed under MIT; the
upstream `LICENSE` is retained.

The local package changes the PyO3 limited-API floor from CPython 3.10 to
CPython 3.8. A Rust toolchain is required to build a wheel because upstream
does not distribute CPython 3.8 wheels.
