import pytest

from pyjsx.linter import (
    Linter,
    remove_empty_jsx_expressions,
    remove_empty_jsx_fragments,
    remove_fragments_with_single_child,
    remove_duplicate_props,
    self_close_empty_components,
)
from pyjsx.transpiler import Parser, unparse


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<p>{}</p>", ["Empty JSX expression"]),
        ("<p>{}foo{}</p>", ["Empty JSX expression", "Empty JSX expression"]),
        ("<p foo={} />", ["Empty JSX expression"]),
    ],
)
def test_empty_expressions(source, expected):
    errors = Linter().lint(source)
    msgs = [err[1] for err in errors]
    assert msgs == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<></>", ["Empty JSX fragment"]),
        ("<p><></></p>", ["Empty JSX fragment"]),
        ("<p><></><></></p>", ["Empty JSX fragment", "Empty JSX fragment"]),
    ],
)
def test_empty_fragments(source, expected):
    errors = Linter().lint(source)
    msgs = [err[1] for err in errors]
    assert msgs == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<><p>foo</p></>", ["Fragment with a single child"]),
        ("<p><><p>foo</p></></p>", ["Fragment with a single child"]),
    ],
)
def test_fragment_single_child(source, expected):
    errors = Linter().lint(source)
    msgs = [err[1] for err in errors]
    assert msgs == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<p></p>", ["Empty components can be self-closing"]),
        ("<p><b></b></p>", ["Empty components can be self-closing"]),
    ],
)
def test_self_closing(source, expected):
    errors = Linter().lint(source)
    msgs = [err[1] for err in errors]
    assert msgs == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<p foo={1} foo={2}>foo</p>", ['Duplicate prop "foo"']),
        ("<p foo={1} bar={2} foo={1} bar={3}>foo</p>", ['Duplicate prop "foo"', 'Duplicate prop "bar"']),
    ],
)
def test_duplicate_props(source, expected):
    errors = Linter().lint(source)
    msgs = [err[1] for err in errors]
    assert msgs == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<p>{}</p>", "<p></p>"),
        ("<p>{}foo{}</p>", "<p>foo</p>"),
        # ("<p foo={} />", "<p foo= />"),  # TODO ??? (currently crashes)
    ],
)
def test_remove_empty_jsx_expression(source, expected):
    ast = Parser(source).parse()
    assert unparse(remove_empty_jsx_expressions(ast)) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<></>", ""),
        ("<p><></></p>", "<p></p>"),
        ("<p><></><></></p>", "<p></p>"),
    ],
)
def test_remove_empty_fragments(source, expected):
    ast = Parser(source).parse()
    assert unparse(remove_empty_jsx_fragments(ast)) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<><p>foo</p></>", "<p>foo</p>"),
        ("<p><><p>foo</p></></p>", "<p><p>foo</p></p>"),
    ],
)
def test_remove_single_child_fragments(source, expected):
    ast = Parser(source).parse()
    assert unparse(remove_fragments_with_single_child(ast)) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<p></p>", "<p />"),
        ("<p><b></b></p>", "<p><b /></p>"),
    ],
)
def test_self_close_components(source, expected):
    ast = Parser(source).parse()
    assert unparse(self_close_empty_components(ast)) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<p foo={1} foo={2}>foo</p>", "<p foo={1}>foo</p>"),
        ("<p foo={1} bar={2} foo={1} bar={3}>foo</p>", "<p foo={1} bar={2}>foo</p>"),
    ],
)
def test_remove_duplicate_props(source, expected):
    ast = Parser(source).parse()
    assert unparse(remove_duplicate_props(ast)) == expected
