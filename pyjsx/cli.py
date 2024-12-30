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
@click.option("-r", "--recursive", type=bool, is_flag=True, default=False, help="Recurse into directories.")
def compile(sources: list[str], recursive: bool) -> None:
    """Compile .px files to regular .py files."""
    count = 0
    for source in sources:
        path = Path(source)
        count += transpile_dir(path, recursive=recursive)
    msg = f"Compiled {count} file" + ("s" if count != 1 else "") + "."
    click.secho(msg, fg="green", bold=True)


def transpile_dir(path: Path, *, recursive: bool = False) -> int:
    if path.is_file():
        return transpile_file(path)
    count = 0
    for file in path.iterdir():
        if file.is_dir() and recursive:
            count += transpile_dir(file)
        elif file.is_file() and file.suffix == ".px":
            count += transpile_file(file)
    return count


def transpile_file(path: Path) -> int:
    if path.suffix != ".px":
        click.secho(f"Skipping {path} (not a .px file)", fg="yellow")
        return 0
    click.echo(f"Compiling {path}...")
    transpiled = transpile(path.read_text())
    path.with_suffix(".py").write_text(transpiled)
    return 1


if __name__ == "__main__":
    cli()
