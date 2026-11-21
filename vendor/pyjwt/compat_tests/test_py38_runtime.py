"""Security-sensitive runtime coverage for the Python 3.8 backport."""

from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

import jwt
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAlgorithmError,
    InvalidSignatureError,
    InvalidSubjectError,
)

_KEY = "0123456789abcdef0123456789abcdef"


def test_hs256_signed_token_requires_the_correct_key() -> None:
    token = jwt.encode({"sub": "user-1"}, _KEY, algorithm="HS256")

    assert jwt.decode(token, _KEY, algorithms=["HS256"])["sub"] == "user-1"
    with pytest.raises(InvalidSignatureError):
        jwt.decode(token, "fedcba9876543210fedcba9876543210", algorithms=["HS256"])


def test_expired_token_is_rejected() -> None:
    token = jwt.encode(
        {"exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        _KEY,
        algorithm="HS256",
    )

    with pytest.raises(ExpiredSignatureError):
        jwt.decode(token, _KEY, algorithms=["HS256"])


def test_decode_rejects_an_algorithm_outside_the_allowlist() -> None:
    token = jwt.encode({"sub": "user-1"}, _KEY, algorithm="HS256")

    with pytest.raises(InvalidAlgorithmError):
        jwt.decode(token, _KEY, algorithms=["RS256"])


def test_rs256_signature_requires_the_matching_public_key() -> None:
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode({"sub": "user-1"}, signing_key, algorithm="RS256")

    assert (
        jwt.decode(token, signing_key.public_key(), algorithms=["RS256"])["sub"]
        == "user-1"
    )

    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(InvalidSignatureError):
        jwt.decode(token, other_key.public_key(), algorithms=["RS256"])


def test_subject_must_be_a_string_when_subject_validation_is_enabled() -> None:
    token = jwt.encode({"sub": 100}, _KEY, algorithm="HS256")

    with pytest.raises(InvalidSubjectError):
        jwt.decode(token, _KEY, algorithms=["HS256"])


def test_backport_version_preserves_the_security_release_floor() -> None:
    assert jwt.__version__ == "2.12.0+py38"
