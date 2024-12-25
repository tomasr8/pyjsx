import itertools
import json
import os
from dataclasses import dataclass

from pyjsx.source_maps.b64_vlq import base64_vlq_encode


type SourceMap = dict[int, tuple[int, int, int]]


# Every position must map to something, but some regions may be empty
# == the source map is a function that is defined for every position, but
#    may not be surjective or injective


def is_continuous(source_map: SourceMap) -> bool:
    n_keys = len(source_map.keys())

    key = 0
    while True:
        start = source_map.get(key, None)
        if start is None:
            break
        key = start[0]
        n_keys -= 1

    return n_keys == 0


def get_end_offset(source_map: SourceMap) -> int:
    if not source_map:
        return 0
    return max([x[0] for x in source_map.values()])


def get_last(source_map: SourceMap) -> int:
    last = 0
    for k in source_map:
        if not last or k > last:
            last = k
    return last


# def extend_last(source_map: SourceMap, offset: int) -> SourceMap:
#     if not source_map:
#         return {0: (offset, 0, offset)}
#     last = get_last(source_map)
#     v = source_map[last]
#     return dict(source_map.items()) | {last: (v[0] + offset, v[1], v[2])}


# def offset_by(source_map: SourceMap, offset: int) -> SourceMap:
#     return {k + offset: (v[0] + offset, v[1], v[2]) for k, v in source_map.items()}


@dataclass(frozen=True)
class OffsetMapping:
    generated_start_offset: int
    generated_end_offset: int
    original_offset: int
    # original_line: int | None = None
    # original_column: int | None = None
    # name: str  # Names not supported


@dataclass(frozen=True)
class Mapping:
    generated_line: int
    generated_column: int
    source: str | None = None
    original_line: int | None = None
    original_column: int | None = None
    # name: str  # Names not supported


def generate_source_map(mappings: list[Mapping], *, sources: list[str], sources_content: list[str], file: str) -> str:
    # Create the JavaScript source map structure
    source_map = {
        "version": 3,
        "sources": sources,
        "names": [],  # TODO names not supported
        "mappings": encode_mappings(mappings, sources),
        "file": file,
        "sourcesContent": sources_content,
    }

    return json.dumps(source_map, indent=2)


def encode_mappings(mappings: list[Mapping], sources: list[str]) -> str:
    mappings = insert_missing_lines(mappings)
    for m in mappings:
        print(m)
    prev_generated_column = 0
    prev_generated_line = 1
    prev_original_column = 0
    prev_original_line = 0
    prev_source = 0
    result = ""

    for i, mapping in enumerate(mappings):
        encoded = ""

        if mapping.generated_line != prev_generated_line:
            prev_generated_column = 0
            while mapping.generated_line != prev_generated_line:
                encoded += ";"
                prev_generated_line += 1
        elif i > 0:
            if mapping == mappings[i - 1]:  # Skip duplicate mappings
                continue
            encoded += ","

        encoded += base64_vlq_encode(mapping.generated_column - prev_generated_column)
        prev_generated_column = mapping.generated_column

        if mapping.source is not None:
            source_idx = sources.index(mapping.source)
            encoded += base64_vlq_encode(source_idx - prev_source)
            prev_source = source_idx

            # lines are stored 0-based in SourceMap spec version 3
            encoded += base64_vlq_encode(mapping.original_line - 1 - prev_original_line)
            prev_original_line = mapping.original_line - 1

            encoded += base64_vlq_encode(mapping.original_column - prev_original_column)
            prev_original_column = mapping.original_column

        result += encoded
    print(result)
    return result


def insert_missing_lines(mappings: list[Mapping]) -> list[Mapping]:
    new_mappings = []
    for prev, curr in itertools.pairwise(mappings):
        new_mappings.append(prev)
        line = prev.original_line + 1
        while line < curr.original_line:
            new_mappings.append(
                Mapping(
                    generated_line=prev.generated_line,
                    generated_column=prev.generated_column,
                    source=prev.source,
                    original_line=line,
                    original_column=0,
                )
            )
            line += 1
        if (prev.original_line < curr.original_line) and curr.original_column > 0:
            new_mappings.append(
                Mapping(
                    generated_line=prev.generated_line,
                    generated_column=prev.generated_column,
                    source=prev.source,
                    original_line=curr.original_line,
                    original_column=0,
                )
            )
    new_mappings.append(mappings[-1])
    return new_mappings
    # if curr.original_line > prev.original_line and curr.original_column > 0:
    #     line = prev.original_line + 1
    #     while line <= curr.original_line:


def convert_offset_to_line_col(offsets: list[int], source: str) -> list[tuple[int, int]]:
    source_index = 0
    offsets_index = 0
    line = 1
    offset = 0
    source_length = len(source)
    offsets_length = len(offsets)
    locations = []
    while source_index < source_length and offsets_index < offsets_length:
        if source_index == offsets[offsets_index]:
            locations.append((line, offset))
            offsets_index += 1
        if source[source_index:].startswith(os.linesep):
            line += 1
            offset = 0
            source_index += len(os.linesep)
        else:
            offset += 1
            source_index += 1
    return locations


def convert_mappings(mappings: list[OffsetMapping], source: str, transpiled: str, name: str) -> list[Mapping]:
    locations_original = convert_offset_to_line_col([m.original_offset for m in mappings], source)
    locations_generated = convert_offset_to_line_col([m.generated_start_offset for m in mappings], transpiled)

    return [
        Mapping(
            generated_line=generated_line,
            generated_column=generated_column,
            source=name,
            original_line=original_line,
            original_column=original_column,
        )
        for (generated_line, generated_column), (original_line, original_column) in zip(
            locations_generated, locations_original, strict=True
        )
    ]


def concat(a: list[OffsetMapping], b: list[OffsetMapping]) -> list[OffsetMapping]:
    if not a:
        return b
    offset = a[-1].generated_end_offset
    return a + [
        OffsetMapping(m.generated_start_offset + offset, m.generated_end_offset + offset, m.original_offset) for m in b
    ]


def extend_last(source_map: list[OffsetMapping], offset: int) -> list[OffsetMapping]:
    assert source_map
    last = source_map[-1]
    source_map[-1] = OffsetMapping(
        last.generated_start_offset, last.generated_end_offset + offset, last.original_offset
    )
    return source_map


def prepend_first(source_map: list[OffsetMapping], offset: int) -> list[OffsetMapping]:
    assert source_map
    first = source_map[0]
    source_map[0] = OffsetMapping(
        first.generated_start_offset - offset, first.generated_end_offset, first.original_offset
    )
    return source_map


def offset_by(source_map: list[OffsetMapping], offset: int) -> list[OffsetMapping]:
    return [
        OffsetMapping(m.generated_start_offset + offset, m.generated_end_offset + offset, m.original_offset)
        for m in source_map
    ]
