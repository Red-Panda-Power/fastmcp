"""Regression checks for compatibility-sensitive host types and policies."""

from inspect import signature

import pytest

from pydantic_monty import ClassInstance, ClassType, Monty


def test_native_type_can_cross_the_host_boundary() -> None:
    with Monty() as pool, pool.checkout() as session:
        assert session.feed_run('isinstance(5, IntType)', external_lookup={'IntType': int}) is True


@pytest.mark.parametrize(('wrapper', 'value'), [(ClassInstance, object()), (ClassType, object)])
def test_object_access_policies_remain_keyword_only(wrapper, value) -> None:
    assert signature(wrapper).parameters['allowed_methods'].kind.name == 'KEYWORD_ONLY'
    with pytest.raises(TypeError):
        wrapper(value, 'all')
