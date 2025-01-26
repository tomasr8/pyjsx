from pathlib import Path

import pytest

from pyjsx.import_hook import PyJSXFinder, register_import_hook, unregister_import_hook


@pytest.fixture
def import_hook():
    register_import_hook()
    yield
    unregister_import_hook()


def test_finder():
    finder = PyJSXFinder()
    path = str(Path(__file__).parent / "test_module")
    spec = finder.find_spec("main", [path])
    assert spec is not None
    assert spec.name == "main"


@pytest.mark.usefixtures("import_hook")
def test_import():
    from .test_module import main  # type: ignore[reportAttributeAccessIssue]

    assert str(main.hello()) == """\
<h1>
    Hello, World!
</h1>"""
