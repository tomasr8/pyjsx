from dataclasses import dataclass


@dataclass(frozen=True)
class Range:
    start: int
    end: int


# @dataclass(frozen=True)
# class SourceMap:
#     source: str
#     mapping: dict[int, tuple[int, int, int]]


type SourceMap = dict[int, tuple[int, int, int]]

# 0-1 -> 0-1
# 1-2 -> 1-3

# 0-2 -> 0-3
# 2-3 -> 3-6


# def merge(x: SourceMap, y: SourceMap) -> SourceMap:


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


def add(source_map: SourceMap, item: tuple[int, int, int, int]) -> SourceMap:
    offset = get_end_offset(source_map)
    return source_map | {item[0] + offset: (item[1] + offset, item[2], item[3])}


def generate_mapping(source_map):
    import base64

    # Base64 character set for VLQ encoding
    VLQ_BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    VLQ_BASE64_SHIFT = 5
    VLQ_BASE64_MASK = (1 << VLQ_BASE64_SHIFT) - 1

    def vlq_encode(value):
        """Encodes a value into a VLQ base64 encoded string."""
        result = []
        value = value << 1 if value < 0 else value << 1 | 1
        while True:
            digit = value & VLQ_BASE64_MASK
            value >>= VLQ_BASE64_SHIFT
            result.append(VLQ_BASE64_ALPHABET[digit])
            if value == 0:
                break
            value |= 1 << (VLQ_BASE64_SHIFT * len(result))

        return "".join(result)

    def generate_vlq_mapping(mapping):
        """Converts the mapping dictionary into a VLQ source map format."""
        vlq_mappings = []

        for entry in mapping:
            gen_line, gen_column, orig_file, orig_line, orig_column = entry
            mapping_str = ""

            # Generated line and column
            mapping_str += vlq_encode(gen_line)
            mapping_str += vlq_encode(gen_column)

            # Original file, line, column (optional)
            if orig_file is not None:
                mapping_str += vlq_encode(orig_file)
                mapping_str += vlq_encode(orig_line)
                mapping_str += vlq_encode(orig_column)

            vlq_mappings.append(mapping_str)

        # Join all mappings together with semicolons (;) as the separator
        return ",".join(vlq_mappings)

    # Example usage
    mapping = [
        (0, 0, 0, 0, 0),  # Generated line 0, column 0 to original file 0, line 0, column 0
        (1, 5, 0, 1, 10),  # Generated line 1, column 5 to original file 0, line 1, column 10
        (2, 10, 1, 2, 15),  # Generated line 2, column 10 to original file 1, line 2, column 15
    ]

    # mapping = [(0, v[0], 0, )
    #     for k, v in source_map.items()
    # ]

    vlq_mapping = generate_vlq_mapping(mapping)
    return vlq_mapping
    # print(vlq_mapping)


import json


def transform_to_js_source_map(source_map):
    mappings = generate_mapping(source_map)
    # Create the JavaScript source map structure
    js_source_map = {
        "version": 3,
        "file": "main.py",
        "sources": ["main.px"],
        "names": ["test"],
        "mappings": mappings,
    }

    # Convert the Python dictionary into a JSON string for the JS source map
    return json.dumps(js_source_map, indent=2)
