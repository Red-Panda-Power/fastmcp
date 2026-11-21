"""Exercise Python 3.8 and Windows compatibility for example output."""

import pytest

from pytest_examples.run_code import Arg


@pytest.mark.parametrize('address', ['0x00007FF123ABCDEF', '0x12345678', '0x7abcdef12345'])
def test_object_addresses_are_normalized(address):
    class ExampleObject:
        def __str__(self):
            return f'<object at {address}>'

    assert str(Arg(ExampleObject())) == '<object at 0x0123456789ab>'
