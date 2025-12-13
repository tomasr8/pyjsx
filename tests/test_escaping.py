import pytest

from pyjsx.import_hook import register_import_hook, unregister_import_hook


@pytest.fixture
def import_hook():
    register_import_hook()
    yield
    unregister_import_hook()


@pytest.mark.usefixtures("import_hook")
def test_import():
    from .test_module import escaping  # type: ignore[reportAttributeAccessIssue]

    assert (
        str(escaping.hello())
        == """\
<h1 attr="x&quot; onclick=&quot;alert(1)&quot;">
    Hello, World!
    <br>
    &lt;script&gt;&lt;/script&gt;
</h1>"""
    )
