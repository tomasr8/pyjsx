# Based on Mozillas source-map node library:
# github.com/mozilla/source-map/lib/base64-vlq.js

# A single base 64 digit can contain 6 bits of data. For the base 64 variable
# length quantities we use in the source map spec, the first bit is the sign,
# the next four bits are the actual value, and the 6th bit is the
# continuation bit. The continuation bit tells us whether there are more
# digits in this value following this digit.
#
#   Continuation
#   |    Sign
#   |    |
#   V    V
#   101011

VLQ_BASE_SHIFT = 5

# binary: 100000
VLQ_BASE = 1 << VLQ_BASE_SHIFT

# binary: 011111
VLQ_BASE_MASK = VLQ_BASE - 1

# binary: 100000
VLQ_CONTINUATION_BIT = VLQ_BASE

BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
BASE64_LEN = 64


def _to_vlq_signed(n: int) -> int:
    """Converts from a two-complement value to a value where the sign bit is
    placed in the least significant bit.

    For example, as decimals:
      1 becomes 2 (10 binary), -1 becomes 3 (11 binary)
      2 becomes 4 (100 binary), -2 becomes 5 (101 binary)

    The maximum number this is called with is 0b011111.
    """
    return (-n << 1) + 1 if n < 0 else (n << 1)


def _to_base64(n: int) -> str:
    if n < 0 or n > BASE64_LEN - 1:
        msg = f"Input integer must be in the range 0-63. Got {n}."
        raise ValueError(msg)
    return BASE64_ALPHABET[n]


def base64_vlq_encode(n: int) -> str:
    """Returns the base 64 VLQ encoded value."""
    encoded = ""
    vlq = _to_vlq_signed(n)

    while True:
        digit = vlq & VLQ_BASE_MASK
        vlq = vlq >> VLQ_BASE_SHIFT
        if vlq > 0:
            # There are still more digits in this value, so we must make sure the
            # continuation bit is marked.
            digit |= VLQ_CONTINUATION_BIT
        encoded += _to_base64(digit)
        if vlq <= 0:
            break

    return encoded
