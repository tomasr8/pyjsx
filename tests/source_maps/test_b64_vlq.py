import pytest

from pyjsx.source_maps.b64_vlq import _to_vlq_signed, base64_vlq_encode


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (0, 0),
        (1, 2),
        (2, 4),
        (3, 6),
        (100, 200),
        (2**15, 65536),
        (-1, 3),
        (-2, 5),
        (-3, 7),
        (-100, 201),
        ((-2) ** 15, 65537),
    ],
)
def test_to_vlq_signed(n, expected):
    assert _to_vlq_signed(n) == expected


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (0, "A"),
        (1, "C"),
        (2, "E"),
        (3, "G"),
        (-1, "D"),
        (-2, "F"),
        (-3, "H"),
        (2**10, "ggC"),
        (2**10 - 1, "+/B"),
        (2**15, "gggC"),
        (2**15 - 1, "+//B"),
        (-(2**10), "hgC"),
        (-(2**10) - 1, "jgC"),
        (-(2**15), "hggC"),
        (-(2**15) - 1, "jggC"),
    ],
)
def test_base64_vlq_encode(n, expected):
    assert base64_vlq_encode(n) == expected
