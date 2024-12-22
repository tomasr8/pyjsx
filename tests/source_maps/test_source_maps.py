import pytest

from pyjsx.source_maps.source_maps import Mapping, encode_mappings


@pytest.mark.parametrize(
    ("mappings", "expected"),
    [
        ([Mapping(generated_line=1, generated_column=0, source="main.px", original_line=1, original_column=0)], "AAAA"),
        ([Mapping(generated_line=1, generated_column=5, source="main.px", original_line=1, original_column=0)], "KAAA"),
        ([Mapping(generated_line=1, generated_column=5, source="main.px", original_line=1, original_column=5)], "KAAK"),
        (
            [
                Mapping(generated_line=1, generated_column=0, source="main.px", original_line=1, original_column=0),
                Mapping(generated_line=1, generated_column=5, source="main.px", original_line=1, original_column=10),
                Mapping(generated_line=2, generated_column=0, source="main.px", original_line=2, original_column=0),
                Mapping(generated_line=3, generated_column=0, source="main.px", original_line=3, original_column=0),
                Mapping(generated_line=3, generated_column=5, source="main.px", original_line=3, original_column=10),
            ],
            "AAAA,KAAU;AACV;AACA,KAAU",
        ),
    ],
)
def test_mappings(mappings, expected):
    assert encode_mappings(mappings, ["main.px"]) == expected


@pytest.mark.parametrize(
    ("mappings", "expected"),
    [
        ([Mapping(generated_line=1, generated_column=0)], "A"),
        (
            [
                Mapping(generated_line=1, generated_column=0),
                Mapping(generated_line=2, generated_column=0, source="main.px", original_line=2, original_column=0),
                Mapping(generated_line=3, generated_column=0),
            ],
            "A;AACA;A",
        ),
    ],
)
def test_unmapped_segments(mappings, expected):
    assert encode_mappings(mappings, ["main.px"]) == expected


@pytest.mark.parametrize(
    ("mappings", "expected"),
    [
        (
            [
                Mapping(generated_line=1, generated_column=0, source="main1.px", original_line=1, original_column=0),
                Mapping(generated_line=1, generated_column=0, source="main2.px", original_line=1, original_column=0),
                Mapping(generated_line=1, generated_column=0, source="main3.px", original_line=1, original_column=0),
            ],
            "AAAA,ACAA,ACAA",
        ),
    ],
)
def test_multiple_sources(mappings, expected):
    assert encode_mappings(mappings, ["main1.px", "main2.px", "main3.px"]) == expected


def test_missing_source():
    with pytest.raises(ValueError, match="'main.px' is not in list"):
        encode_mappings(
            [Mapping(generated_line=1, generated_column=0, source="main.px", original_line=1, original_column=0)], []
        )
