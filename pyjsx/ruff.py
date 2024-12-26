import itertools
import json
import subprocess
import sys
from pathlib import Path

from pyjsx.source_maps.source_maps import (
    Mapping,
    OffsetMapping,
    convert_line_col_to_offset,
    convert_mappings,
    generate_source_map,
)
from pyjsx.transpiler import Parser, transpile_sm


def remap_error(
    start: tuple[int, int],
    end: tuple[int, int],
    offset_map: list[OffsetMapping],
    line_col_map: list[Mapping],
    source: str,
):
    start_line = start[0]
    start_col = start[1]
    end_line = end[0]
    end_col = end[1]
    index = None
    for i, (prev, curr) in enumerate(itertools.pairwise(line_col_map)):
        # print(start_line, start_col, line_col)
        if (
            start_line >= prev.generated_line
            and start_col >= prev.generated_column
            and (
                (start_line < curr.generated_line)
                or (start_line <= curr.generated_line and start_col < curr.generated_column)
            )
        ):
            index = i
            break

    if index is None:
        before = offset_map[-1]
        return before.original_offset, None

    print("Error location", start_line, start_col, convert_line_col_to_offset([(start_line, start_col)], source)[0])
    before = line_col_map[index]
    after = line_col_map[index + 1]
    print("before/after", before, after)
    generated_start_offset = offset_map[index].generated_start_offset
    # generated_end_offset = offset_map[index].generated_end_offset

    # diff
    error_start_offset = convert_line_col_to_offset([(start_line, start_col)], source)[0]
    start_diff = error_start_offset - generated_start_offset
    error_end_offset = convert_line_col_to_offset([(end_line, end_col)], source)[0]
    end_diff = error_end_offset - generated_start_offset

    start_offset = offset_map[index].original_offset + start_diff
    end_offset = offset_map[index].original_offset + end_diff
    # end_offset = offset_map[index + 1].original_offset

    return start_offset, end_offset


if __name__ == "__main__":
    path = Path(sys.argv[1])
    source = path.read_text("utf-8")
    transpiled, source_map = transpile_sm(source)
    mappings = convert_mappings(source_map, source, transpiled, name="main.px")
    res = subprocess.run(
        ["ruff", "check", "--output-format=json", "--stdin-filename=main.py"],
        input=transpiled.encode("utf-8"),
        capture_output=True,
    )
    # print(res)
    # assert res.check_returncode == 0
    errors = json.loads(res.stdout)
    # print(errors[1])
    print(errors)

    for err in errors:
        # err = errors[1]
        location = err["location"]
        end_location = err["end_location"]

        start, end = remap_error(
            (location["row"], location["column"] - 1),
            (end_location["row"], end_location["column"] - 1),
            source_map,
            mappings,
            transpiled,
        )

        print(f'<<<{source[start:end]}>>>')


# tr = Transpiler(ast)
# tr.transpile()

# transpiled, source_map = ast.transpile()
# for m in source_map:
#     print(m, source[m.original_offset :])
# # print(source_map)
# source_map = convert_mappings(source_map, source, transpiled, name="main.px")
# generated = generate_source_map(source_map, sources=["main.px"], sources_content=[source], file="main.px")
# print(transpiled)


# Path("main.px.map").write_text(generated, "utf-8")
# Path("main.py").write_text(transpiled, "utf-8")
