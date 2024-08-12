import itertools
from pathlib import Path
from subprocess import PIPE, Popen

import pytest

from pyjsx.tokenizer import Tokenizer


def ruff_format(source):
    p = Popen(["ruff", "format", "-"], shell=False, stdin=PIPE, stdout=PIPE, stderr=PIPE)  # noqa: S603, S607
    output, err = p.communicate(source.encode("utf-8"))
    assert not err
    return output


@pytest.mark.parametrize(
    "source",
    [
        "<div></div>",
        "<input />",
        "<></>",
        "<div>Hello, world!</div>",
    ],
    ids=itertools.count(1),
)
def test_simple(request, snapshot, source):
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    tokenizer = Tokenizer(source)
    tokens = list(tokenizer.tokenize())
    snapshot.assert_match(ruff_format(repr(tokens)), f"tokenizer-simple-{request.node.callspec.id}.txt")


@pytest.mark.parametrize(
    "source",
    [
        "<a.b.c></a.b.c>",
        "<a.b.c />",
    ],
    ids=itertools.count(1),
)
def test_element_names(request, snapshot, source):
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    tokenizer = Tokenizer(source)
    tokens = list(tokenizer.tokenize())
    snapshot.assert_match(ruff_format(repr(tokens)), f"tokenizer-element-names-{request.node.callspec.id}.txt")


@pytest.mark.parametrize(
    "source",
    [
        "<div foo='bar'></div>",
        '<div foo="bar"></div>',
        "<input type='number' value='2' />",
        "<button disabled>Hello, world!</button>",
        "<Component wrapper=<div></div>></Component>",
        "<Component wrapper=<div></div> ></Component>",
    ],
    ids=itertools.count(1),
)
def test_attributes_names(request, snapshot, source):
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    tokenizer = Tokenizer(source)
    tokens = list(tokenizer.tokenize())
    snapshot.assert_match(ruff_format(repr(tokens)), f"tokenizer-element-attributes-{request.node.callspec.id}.txt")


@pytest.mark.parametrize(
    "source",
    [
        """\
<div>
    Click <a>here</a>
    or
    <button>Submit</button>
</div>""",
    ],
    ids=itertools.count(1),
)
def test_nesting(request, snapshot, source):
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    tokenizer = Tokenizer(source)
    tokens = list(tokenizer.tokenize())
    snapshot.assert_match(ruff_format(repr(tokens)), f"tokenizer-nesting-{request.node.callspec.id}.txt")


@pytest.mark.parametrize(
    "source",
    [
        "<a href={href}>{link_title}</a>",
        "<Header {...props}>{title} />",
        "<span {...{'key': 'value'}}>{title} />",
        "<span>{<h1>{title}</h1> if cond else <h2>{title}</h2>}</span>",
    ],
    ids=itertools.count(1),
)
def test_mixed(request, snapshot, source):
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    tokenizer = Tokenizer(source)
    tokens = list(tokenizer.tokenize())
    snapshot.assert_match(ruff_format(repr(tokens)), f"tokenizer-mixed-{request.node.callspec.id}.txt")


@pytest.mark.parametrize(
    "source",
    [
        """\
'''
<>This should not be transpiled</>
'''
""",
        """\
'''
<div {...x}>
    Neither this
    {1+2}
</div>
'''
""",
        '''\
"""
<>This should not be transpiled</>
"""
''',
        '''\
"""
<div {...x}>
    Neither this
    {1+2}
</div>
"""
''',
        '''\
rB"""
<div {...x}>
    Neither this
    {1+2}
</div>
"""
''',
    ],
    ids=itertools.count(1),
)
def test_multiline_strings(request, snapshot, source):
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    tokenizer = Tokenizer(source)
    tokens = list(tokenizer.tokenize())
    snapshot.assert_match(ruff_format(repr(tokens)), f"tokenizer-strings-{request.node.callspec.id}.txt")


@pytest.mark.parametrize(
    "source",
    [
        "f'test'",
        'f"test"',
        "f'''test'''",
        'f"""test"""',
        "f'{1}'",
        'f"{1}+{1}={2}"',
        'f"{f"{1}"}"',
        '''f"""
Hello, {world}!
"""''',
        'f"Hello, {<b>world</b>}!"',
    ],
    ids=itertools.count(1),
)
def test_fstrings(request, snapshot, source):
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    tokenizer = Tokenizer(source)
    tokens = list(tokenizer.tokenize())
    snapshot.assert_match(ruff_format(repr(tokens)), f"tokenizer-fstrings-{request.node.callspec.id}.txt")
