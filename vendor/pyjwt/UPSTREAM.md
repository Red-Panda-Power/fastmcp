# PyJWT 2.12.0 Python 3.8 backport

This directory is vendored from [PyJWT 2.12.0](https://github.com/jpadilla/pyjwt/releases/tag/2.12.0), licensed under MIT.

Source distribution:

- URL: `https://files.pythonhosted.org/packages/a8/10/e8192be5f38f3e8e7e046716de4cae33d56fd5ae08927a823bb916be36c1/pyjwt-2.12.0.tar.gz`
- SHA-256: `2f62390b667cd8257de560b850bb5a883102a388829274147f1d724453f8fb02`

The upstream release declares Python 3.9 or later. This fork changes only the
Python-version metadata, Python-3.8-compatible build metadata, and eagerly
evaluated built-in generic aliases so it can run on Python 3.8. The version is
`2.12.0+py38`, which remains compatible with requirements for
`PyJWT>=2.12.0`.
