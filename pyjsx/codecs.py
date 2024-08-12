import codecs
import encodings

from pyjsx.transpiler import transpile


def pyjsx_decode(input: bytes, errors: str = "strict") -> tuple[str, int]:  # noqa: A002, ARG001
    return transpile(input.decode("utf-8")), len(input)


def pyjsx_search_function(encoding: str) -> codecs.CodecInfo | None:
    if encoding != "pyjsx":
        return None

    utf8 = encodings.search_function("utf8")
    assert utf8 is not None
    return codecs.CodecInfo(
        name="pyjsx",
        encode=utf8.encode,
        decode=pyjsx_decode,
        incrementalencoder=utf8.incrementalencoder,
        incrementaldecoder=utf8.incrementaldecoder,
        streamreader=utf8.streamreader,
        streamwriter=utf8.streamwriter,
    )


def register_jsx() -> None:
    codecs.register(pyjsx_search_function)
