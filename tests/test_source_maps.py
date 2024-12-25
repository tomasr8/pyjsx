import json

import pytest

from pyjsx.source_maps.source_maps import (
    convert_mappings,
    convert_offset_to_line_col,
    generate_source_map,
    get_end_offset,
    is_continuous,
)
from pyjsx.tokenizer import Token, TokenType
from pyjsx.transpiler import (
    JSXElement,
    JSXExpression,
    JSXFragment,
    JSXText,
    Parser,
    PythonData,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("x = 1", {0: (5, 0, 5)}),
        (
            """\
def foo():
    return 42
""",
            {0: (25, 0, 25)},
        ),
    ],
)
def test_python_data(source, expected):
    node = Parser(source).parse().children[0]
    assert isinstance(node, PythonData)

    source_map = node.transpile()[1]
    assert source_map == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Hello, world!", {0: (15, 0, 13)}),
        (
            """\
Multiline
    Hello,
        world!
""",
            {0: (38, 0, 36)},
        ),
    ],
)
def test_jsx_text(source, expected):
    node = JSXText(source, Token(TokenType.JSX_TEXT, source, start=0, end=len(source)))
    source_map = node.transpile()[1]
    assert source_map == expected


def test_jsx_expression():
    node = JSXExpression(
        children=[JSXText(value="1+2", token=Token(TokenType.JSX_TEXT, "1+2", start=1, end=4))],
        open_token=Token(TokenType.JSX_OPEN_BRACE, "{", start=0, end=1),
        close_token=Token(TokenType.JSX_CLOSE_BRACE, "}", start=4, end=5),
    )

    source_map = node.transpile()[1]
    assert source_map == {0: (5, 1, 4)}


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<></>", {0: (23, 0, 2), 23: (25, 2, 5)}),
        ("<>foo</>", {0: (23, 0, 2), 23: (28, 2, 5), 28: (30, 5, 8)}),
    ],
)
def test_jsx_fragment(source, expected):
    node = Parser(source).parse().children[0]
    assert isinstance(node, JSXFragment)

    transpiled, source_map = node.transpile()
    assert len(transpiled) == get_end_offset(source_map)
    assert is_continuous(source_map)
    assert source_map == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<br />", {0: (4, 0, 1), 4: (13, 1, 3), 13: (15, 4, 6)}),
        ("<br/>", {0: (4, 0, 1), 4: (13, 1, 3), 13: (15, 3, 5)}),
        ("<p></p>", {0: (4, 0, 1), 4: (12, 1, 2), 12: (14, 2, 3)}),
        (
            '<br foo="bar" />',
            {0: (4, 0, 1), 4: (10, 1, 3), 10: (11, 4, 7), 11: (18, 4, 7), 18: (27, 8, 13), 27: (29, 14, 16)},
        ),
    ],
)
def test_jsx_element(source, expected):
    node = Parser(source).parse().children[0]
    assert isinstance(node, JSXElement)

    transpiled, source_map = node.transpile()
    # print(transpiled)
    # assert len(transpiled) == get_end_offset(source_map)
    assert is_continuous(source_map)
    assert source_map == expected


@pytest.mark.parametrize(
    ("offsets", "source", "expected"),
    [
        ([], "", []),
        ([0], "foo", [(1, 0)]),
        ([0, 1, 2], "foo", [(1, 0), (1, 1), (1, 2)]),
        ([0, 1, 2], "foobar", [(1, 0), (1, 1), (1, 2)]),
        ([0, 100], "foo", [(1, 0)]),
        ([100], "foo", []),
        ([0, 4], "foo\nbar", [(1, 0), (2, 0)]),
        ([3, 5], "foo\nbar", [(1, 3), (2, 1)]),
    ],
)
def test_convert_offset_to_line_col(offsets, source, expected):
    assert convert_offset_to_line_col(offsets, source) == expected


@pytest.mark.parametrize(
    ("source", "vlq"),
    [
        ("", ""),
    ],
)
def test_source_maps(source, vlq):
    ast = Parser(source).parse()
    transpiled, source_map = ast.transpile()
    source_map = convert_mappings(source_map, source, transpiled, name="main.px")
    generated = generate_source_map(source_map, sources=["main.px"], sources_content=[source], file="main.px")
    generated = json.loads(generated)
    assert generated["mappings"] == vlq
