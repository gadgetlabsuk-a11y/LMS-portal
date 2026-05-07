"""Unit tests for CSV escaping."""
from app.routers.reports import _csv_escape


def test_plain_value():
    assert _csv_escape("hello") == "hello"


def test_none_value():
    assert _csv_escape(None) == ""


def test_value_with_comma():
    assert _csv_escape("a,b") == '"a,b"'


def test_value_with_quotes():
    result = _csv_escape('say "hi"')
    assert result == '"say ""hi"""'


def test_value_with_newline():
    result = _csv_escape("line\nnewline")
    assert '"' in result


def test_numeric_value():
    assert _csv_escape(42) == "42"


def test_float_value():
    assert _csv_escape(3.14) == "3.14"
