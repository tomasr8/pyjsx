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


PYJSX_SUFFIX = ".px"


class PyJSXLoader(FileLoader):
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
        if not path:
            path = sys.path

        for p in path:
            if spec := self._spec_from_path(fullname, p):
                return spec

    def _spec_from_path(self, fullname: str, path: str) -> ModuleSpec | None:
        last_segment = fullname.rsplit(".", maxsplit=1)[-1]
        full_path = Path(path) / f"{last_segment}{PYJSX_SUFFIX}"
        if full_path.exists():
            loader = PyJSXLoader(fullname, str(full_path))
            return importlib.util.spec_from_loader(fullname, loader)


def register_import_hook() -> None:
    """Register import hook for .px files."""
    sys.meta_path.append(PyJSXFinder())


def unregister_import_hook() -> None:
    """Unregister import hook for .px files."""
    sys.meta_path = [finder for finder in sys.meta_path if not isinstance(finder, PyJSXFinder)]
