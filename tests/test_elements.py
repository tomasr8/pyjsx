import pytest

from pyjsx.elements import is_builtin_element


@pytest.mark.parametrize(
    ("elem", "is_builtin"),
    [
        ("a", True),
        ("div", True),
        ("input", True),
        ("foo", False),
        ("Component", False),
        ("custom-element", True),
        ("foo-", True),
        ("-bar", True),
        ("-", True),
    ],
)
def test_builtin_elements(elem, is_builtin):
    assert is_builtin_element(elem) == is_builtin
