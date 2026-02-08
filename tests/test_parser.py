import pytest
from contextlib import nullcontext as does_not_raise

from src.utils.parser import *
from config import *

@pytest.mark.parametrize(
    "ticker, type_ticker, interval, start, end, expectation",
    [
        ("SBER", "shares", 60, "2026-01-01", "2026-02-08", does_not_raise()),
        ("SBER", "null", 60, "2026-01-01", "2026-02-08", pytest.raises(Exception)),
        ("SBER", "null", -7, "2026-01-01", "2026-02-08", pytest.raises(Exception)),
        ("wewewe", "shares", 60, "2026-01-01", "2026-02-08", pytest.raises(Exception))
    ]
)
def test_get_candles(ticker, type_ticker, interval, start, end, expectation):
    with expectation:
        assert get_candles(ticker, type_ticker, interval, start, end)


@pytest.mark.parametrize(
    "ticker, expectation",
    [
        ("SBER", does_not_raise()),
        ("wewewe", pytest.raises(Exception))
    ]
)
def test_get_TMI(ticker, expectation):
    with expectation:
        assert get_TMI(ticker)