import functools
from collections.abc import Callable, Generator
from pathlib import Path

import click

from pyjsx.linter import fix, lint
from pyjsx.transpiler import transpile


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True)
def cli(*, version: bool) -> None:
    if version:
        import pyjsx

        click.echo(pyjsx.__version__)


def accept_files_and_dirs(f: Callable) -> Callable:
    @click.argument("sources", type=click.Path(exists=True), nargs=-1)
    @click.option("-r", "--recursive", type=bool, is_flag=True, default=False, help="Recurse into directories.")
    @functools.wraps(f)
    def wrapper(*args, **kwargs) -> None:
        return f(*args, **kwargs)

    return wrapper


@cli.command("compile")
@accept_files_and_dirs
def compile_files(sources: list[str], *, recursive: bool) -> None:
    """Compile .px files to regular .py files."""
    paths = [Path(source) for source in sources]
    count = 0
    for path in iter_files(paths, recursive=recursive):
        transpile_file(path)
        count += 1
    msg = f"Compiled {count} file" + ("s" if count != 1 else "") + "."
    click.secho(msg, fg="green", bold=True)


@cli.command("lint")
@accept_files_and_dirs
def lint_files(sources: list[str], *, recursive: bool) -> None:
    """Find issues with JSX."""
    paths = [Path(source) for source in sources]
    for path in iter_files(paths, recursive=recursive):
        for error in lint(path.read_text("utf-8")):
            click.secho(f"{error[1]}", fg="red")


@cli.command("fix")
@accept_files_and_dirs
def fix_files(sources: list[str], *, recursive: bool) -> None:
    """Fix issues with JSX."""
    paths = [Path(source) for source in sources]
    for path in iter_files(paths, recursive=recursive):
        fixed = fix(path.read_text("utf-8"))
        path.write_text(fixed, encoding="utf-8")


def transpile_file(path: Path) -> None:
    click.echo(f"Compiling {path}...")
    transpiled = transpile(path.read_text())
    path.with_suffix(".py").write_text(transpiled)


def iter_files(sources: list[Path], *, recursive: bool = False) -> Generator[Path, None, None]:
    for source in sources:
        path = Path(source)
        if path.is_file() and path.suffix == ".px":
            yield path
        elif path.is_dir():
            yield from iter_files([path], recursive=recursive)
