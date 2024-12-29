from pathlib import Path

import click

from pyjsx.transpiler import transpile


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True)
def cli(*, version: bool) -> None:
    if version:
        import pyjsx

        click.echo(pyjsx.__version__)


@cli.command()
@click.argument("sources", type=click.Path(exists=True), nargs=-1)
@click.option("-r", "--recursive", type=bool, default=True, help="Recurse into directories.")
def compile(sources: list[str], recursive: bool) -> None:
    """Compile a PX file to a PY file."""
    for source in sources:
        path = Path(source)
        if path.is_dir():
            transpile_dir(path, recursive=recursive)
        elif path.suffix == ".px":
            transpile_file(path)
        else:
            click.echo(f"Skipping {source} (not a PX file)")
    click.echo("Compilation complete.")


def transpile_dir(path: Path, *, recursive: bool = False) -> None:
    assert path.is_dir()
    for file in path.iterdir():
        if file.is_dir() and recursive:
            transpile_dir(file)
        elif file.suffix == ".px":
            transpile_file(file)


def transpile_file(path: Path) -> None:
    """Transpile a PX file to a PY file."""
    assert path.suffix == ".px"
    transpiled = transpile(path.read_text())
    path.with_suffix(".py").write_text(transpiled)


if __name__ == "__main__":
    cli()
