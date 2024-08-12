import contextlib
import itertools
import sys
from pathlib import Path

import pytest

from pyjsx.transpiler import transpile


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<div></div>", 'jsx("div", {}, [])'),
        ("<input />", 'jsx("input", {}, [])'),
        ("<></>", "jsx(jsx.Fragment, {}, [])"),
        ("<div>Hello, world!</div>", 'jsx("div", {}, ["Hello, world!"])'),
    ],
)
def test_simple(source, expected):
    assert transpile(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<div foo='bar'></div>", "jsx(\"div\", {'foo': 'bar'}, [])"),
        (
            "<div foo='bar' ham='spam'></div>",
            "jsx(\"div\", {'foo': 'bar', 'ham': 'spam'}, [])",
        ),
        ("<input type='number' />", "jsx(\"input\", {'type': 'number'}, [])"),
        (
            "<button disabled>Hello, world!</button>",
            'jsx("button", {\'disabled\': True}, ["Hello, world!"])',
        ),
    ],
)
def test_simple_attributes(source, expected):
    assert transpile(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<div foo='bar' {...x}></div>", "jsx(\"div\", {'foo': 'bar'} | (x), [])"),
        (
            "<input {...x} type='number' {...y} />",
            "jsx(\"input\", (x) | {'type': 'number'} | (y), [])",
        ),
        (
            "<button disabled {...x}>Hello, world!</button>",
            'jsx("button", {\'disabled\': True} | (x), ["Hello, world!"])',
        ),
        (
            "<input {...{'foo': 'bar'}} {...x.y} {...yield foo()} />",
            "jsx(\"input\", ({'foo': 'bar'}) | (x.y) | (yield foo()), [])",
        ),
    ],
)
def test_spread_attributes(source, expected):
    assert transpile(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<div foo={'bar'} {...x}></div>", "jsx(\"div\", {'foo': 'bar'} | (x), [])"),
        (
            "<input value={2+3} type='number' {...y} />",
            "jsx(\"input\", {'value': 2+3, 'type': 'number'} | (y), [])",
        ),
        (
            "<button foo={[1, 2, 3]} disabled {...x}>Hello, world!</button>",
            "jsx(\"button\", {'foo': [1, 2, 3], 'disabled': True} | (x), [\"Hello, world!\"])",
        ),
    ],
)
def test_expression_attributes(source, expected):
    assert transpile(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "<div foo=<b>bold</b>></div>",
            'jsx("div", {\'foo\': jsx("b", {}, ["bold"])}, [])',
        ),
        (
            "<div foo=<b>bold</b> ></div>",
            'jsx("div", {\'foo\': jsx("b", {}, ["bold"])}, [])',
        ),
        (
            "<div foo=<b>bold</b> bar=<a href='test.com'>link</a> ></div>",
            'jsx("div", {\'foo\': jsx("b", {}, ["bold"]), \'bar\': jsx("a", {\'href\': \'test.com\'}, ["link"])}, [])',
        ),
        (
            "<input frag=<></> type='number' {...y} />",
            "jsx(\"input\", {'frag': jsx(jsx.Fragment, {}, []), 'type': 'number'} | (y), [])",
        ),
    ],
)
def test_jsx_attributes(source, expected):
    assert transpile(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<div><button></button></div>", 'jsx("div", {}, [jsx("button", {}, [])])'),
        ("<><b></b></>", 'jsx(jsx.Fragment, {}, [jsx("b", {}, [])])'),
        (
            "<><b><i>test</i></b></>",
            'jsx(jsx.Fragment, {}, [jsx("b", {}, [jsx("i", {}, ["test"])])])',
        ),
        (
            "<div><b>Hello, world!</b></div>",
            'jsx("div", {}, [jsx("b", {}, ["Hello, world!"])])',
        ),
    ],
)
def test_simple_nesting(source, expected):
    assert transpile(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("<div><button></button></div>", 'jsx("div", {}, [jsx("button", {}, [])])'),
        ("<><b></b></>", 'jsx(jsx.Fragment, {}, [jsx("b", {}, [])])'),
        (
            "<><b><i>test</i></b></>",
            'jsx(jsx.Fragment, {}, [jsx("b", {}, [jsx("i", {}, ["test"])])])',
        ),
        (
            "<div><b>Hello, world!</b></div>",
            'jsx("div", {}, [jsx("b", {}, ["Hello, world!"])])',
        ),
    ],
)
def test_multiple_children(source, expected):
    assert transpile(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        """\
<div>
    Click
    <button>here</button>
    or <a href="example.com">there</a>
</div>""",
        """\
<ul>
    <li>First</li>
    <li>Second</li>
    <li>Third</li>
</ul>""",
        """\
def Header(props):
    title = props["title"]
    return <h1 data-x="123" style={{'font-size': '12px'}}>{title}</h1>


def Body(props):
    return <div class="body">{props["children"]}</div>


def App():
    return (
        <Body>
            some
            text
            <Header title="Home" />
            more
            text
        </Body>
    )""",
    ],
    ids=itertools.count(1),
)
def test_multiline(snapshot, request, source):
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    snapshot.assert_match(transpile(source), f"transpiler-multiline-{request.node.callspec.id}.txt")


@pytest.mark.parametrize(
    "source",
    [
        '"\\""',
        "'\\''",
        '"""""\\""""',
        "'''''\\''''",
    ],
)
def test_string_escapes(source):
    assert transpile(source) == source


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('<li>"quoted text"</li>', 'jsx("li", {}, ["\\"quoted text\\""])'),
    ],
)
def test_jsx_text_escapes(source, expected):
    assert transpile(source) == expected


def _get_stdlib_python_modules():
    modules = sys.stdlib_module_names
    for name in modules:
        module = None
        with contextlib.suppress(Exception):
            module = __import__(name)

        if (file_ := getattr(module, "__file__", None)) is None:
            continue

        file_ = Path(file_)
        if file_.suffix != ".py":
            continue

        yield file_


@pytest.mark.parametrize("module_path", _get_stdlib_python_modules())
def test_roundtrip(module_path):
    source = module_path.read_text()
    assert transpile(source) == source
