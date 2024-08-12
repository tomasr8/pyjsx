import sys
from pathlib import Path

from pyjsx import transpile


def transpile_file(f: Path) -> None:
    print("Transpiling", f)  # noqa: T201
    source = f.read_text()
    new_file = f.parent / f"{f.stem}_transpiled{f.suffix}"
    new_file.write_text(transpile(source))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        path = Path(p)
        if not path.exists():
            continue
        if path.is_dir():
            for f in path.rglob("*.py"):
                transpile_file(f)
        else:
            transpile_file(path)
