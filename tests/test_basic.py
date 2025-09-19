import sys


def test_python_version():
    major, minor = sys.version_info[:2]
    assert (major, minor) >= (3, 9)


def test_basic_math():
    assert 2 + 2 == 4