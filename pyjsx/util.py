from collections.abc import Generator, Iterable


def indent(text: str, spaces: int = 4) -> str:
    return "\n".join(f"{' ' * spaces}{line}" for line in text.split("\n"))


def flatten(children: Iterable) -> Generator:
    for child in children:
        if isinstance(child, list | tuple):
            yield from flatten(child)
        else:
            yield child
