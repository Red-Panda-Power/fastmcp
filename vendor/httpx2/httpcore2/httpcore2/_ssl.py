import os
import ssl
import sys


def default_ssl_context() -> ssl.SSLContext:
    if cafile := os.environ.get("SSL_CERT_FILE"):  # pragma: no cover
        return ssl.create_default_context(cafile=cafile)
    if capath := os.environ.get("SSL_CERT_DIR"):  # pragma: no cover
        return ssl.create_default_context(capath=capath)
    if sys.version_info < (3, 10):  # truststore requires Python 3.10
        return ssl.create_default_context()

    import truststore

    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
