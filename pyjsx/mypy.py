from mypy.plugin import Plugin


class PyJSXPlugin(Plugin):
    import pyjsx.auto_setup


def plugin(_version: str) -> type[Plugin]:
    return PyJSXPlugin
