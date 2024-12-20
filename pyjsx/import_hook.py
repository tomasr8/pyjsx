# Inspired by https://github.com/pyxy-org/pyxy/blob/main/pyxy/importer/hook.py
# Allow importing JSX as Python modules
# This is in addition to the coding hook which transpiles .py files
# This allows one to write JSX code in .px files and import them as Python modules.
#
# For example:
#     # hello.px
#     def hello():
#         return <div>Hello, World!</div>
#
#     # main.py
#     import hello
#     print(hello.hello())

import importlib.util
import sys
from collections.abc import Sequence
from importlib.abc import FileLoader, MetaPathFinder
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

from pyjsx.transpiler import transpile


class PyJSXLoader(FileLoader):
    def __init__(self, name: str):
        self.name = name
        self.path = f"{name}.px"

    def _compile(self) -> str:
        return transpile(Path(self.path).read_text("utf-8"))

    def exec_module(self, module: ModuleType) -> None:
        code = self._compile()
        exec(code, module.__dict__)  # noqa: S102

    def get_source(self, fullname: str) -> str:  # noqa: ARG002
        return self._compile()


class PyJSXFinder(MetaPathFinder):
    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: ModuleType | None = None,  # noqa: ARG002
    ) -> ModuleSpec | None:
        filename = f"{fullname}.px"
        if not Path(filename).exists():
            return None
        if path:
            msg = "Only top-level imports are supported"
            raise NotImplementedError(msg)
        return importlib.util.spec_from_loader(fullname, PyJSXLoader(fullname))


def register_import_hook() -> None:
    sys.meta_path.append(PyJSXFinder())
