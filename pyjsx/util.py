from collections.abc import Generator, Iterable


def indent(text: str, spaces: int = 4) -> str:
    return "\n".join(f"{' ' * spaces}{line}" for line in text.split("\n"))


def flatten(children: Iterable) -> Generator:
    for child in children:
        if isinstance(child, list | tuple):
            yield from flatten(child)
        else:
            yield child


def get_line_number_offset(source: str, start: int, end: int) -> tuple[int, int]:
    line_start = start

    while line_start > 0 and source[line_start - 1] != "\n":
        line_start -= 1

    line_number = 0
    offset = start
    while offset > 0:
        if source[offset] == "\n":
            line_number += 1
        offset -= 1

    return line_number + 1, start - line_start


def highlight_line(source: str, start: int, end: int) -> str:
    line_start = start
    line_end = end

    while line_start > 0 and source[line_start - 1] != "\n":
        line_start -= 1
    while line_end < len(source) and source[line_end] != "\n":
        line_end += 1

    offset = start - line_start
    highlight = offset * " " + (end - start) * "^"

    return f"{source[line_start:line_end]}\n{highlight}"
