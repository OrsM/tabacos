import pytest
from tabacos.numbers import es_int, es_decimal, es_percent


def test_es_int_strips_thousands_dots():
    assert es_int("989.317.395") == 989_317_395
    assert es_int("-1") == -1
    assert es_int("42") == 42


def test_es_decimal_uses_comma():
    assert es_decimal("5,97") == 5.97


def test_es_percent():
    assert es_percent("-2,56%") == -2.56


@pytest.mark.parametrize("bad", ["", "1,5", "1.2", "abc"])
def test_es_int_rejects_non_integers(bad):
    with pytest.raises(ValueError):
        es_int(bad)
