import pytest

from pyjsx.jsx import jsx


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (jsx(jsx.Fragment, {}, []), ""),
        (jsx(jsx.Fragment, {}, ["test"]), "test"),
        (jsx(jsx.Fragment, {}, ["1st line", "2nd line"]), "1st line\n2nd line"),
        (
            jsx(jsx.Fragment, {}, ["first", jsx("b", {}, ["bold"]), "last"]),
            """\
first
<b>
    bold
</b>
last""",
        ),
    ],
)
def test_fragments(source, expected):
    assert str(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (jsx("div", {}, []), "<div></div>"),
        (jsx("div", {"foo": "bar"}, []), '<div foo="bar"></div>'),
        (jsx("input", {}, []), "<input />"),
        (jsx("input", {"type": "number", "disabled": True}, []), '<input type="number" disabled />'),
        (
            jsx("span", {"style": {"font-size": "14px", "font-weight": "bold"}}, ["text"]),
            """\
<span style="font-size: 14px; font-weight: bold">
    text
</span>""",
        ),
        (
            jsx("ul", {}, [jsx("li", {}, ["item 1"]), jsx("li", {}, ["item 2"])]),
            """\
<ul>
    <li>
        item 1
    </li>
    <li>
        item 2
    </li>
</ul>""",
        ),
    ],
)
def test_builtins(source, expected):
    assert str(source) == expected


def test_custom_components():
    def Component(props):
        return jsx("div", {"class": "wrapper"}, props["children"])

    source = jsx(Component, {}, ["Hello, world!"])
    assert (
        str(source)
        == """\
<div class="wrapper">
    Hello, world!
</div>"""
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (jsx("input", {"foo": '"should escape"'}, []), '<input foo="&quot;should escape&quot;" />'),
    ],
)
def test_attribute_escapes(source, expected):
    assert str(source) == expected
