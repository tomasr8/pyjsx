import json
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


def extend_last(source_map: SourceMap, offset: int) -> SourceMap:
    if not source_map:
        return {0: (offset, 0, offset)}
    last = get_last(source_map)
    v = source_map[last]
    return dict(source_map.items()) | {last: (v[0] + offset, v[1], v[2])}


def offset_by(source_map: SourceMap, offset: int) -> SourceMap:
    return {k + offset: (v[0] + offset, v[1], v[2]) for k, v in source_map.items()}


@dataclass(frozen=True)
class Mapping:
    generated_line: int
    generated_column: int
    source: str | None = None
    original_line: int | None = None
    original_column: int | None = None
    # name: str  # Names not supported


def generate_source_map(mappings: list[Mapping], sources: list[str], sources_content: list[str]) -> str:
    # Create the JavaScript source map structure
    source_map = {
        "version": 3,
        "sources": ["main.px"],
        "names": [],  # TODO names not supported
        "mappings": encode_mappings(mappings, sources),
        "file": "main.py",
        "sourcesContent": ["x = 1"],
    }

    return json.dumps(source_map, indent=2)


def encode_mappings(mappings: list[Mapping], sources: list[str]) -> str:
    prev_generated_column = 0
    prev_generated_line = 1
    prev_original_column = 0
    prev_original_line = 0
    prev_source = 0
    result = ""
    mapping = None
    sourceIdx = None

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
            sourceIdx = sources.index(mapping.source)
            encoded += base64_vlq_encode(sourceIdx - prev_source)
            prev_source = sourceIdx

            # lines are stored 0-based in SourceMap spec version 3
            encoded += base64_vlq_encode(mapping.original_line - 1 - prev_original_line)
            prev_original_line = mapping.original_line - 1

            encoded += base64_vlq_encode(mapping.original_column - prev_original_column)
            prev_original_column = mapping.original_column

        result += encoded

    return result
