from typing import Any

import pytest

from pyjsx import JSX, JSXComponent, jsx, transpile


def run_example(source: str, _locals: dict[str, Any] | None = None) -> str:
    py_code = transpile(source)
    out = eval(py_code, {"jsx": jsx}, _locals)  # noqa: S307
    assert isinstance(out, str)
    return out


def test_passing_jsx_as_props():
    def CardWithImageComponent(image: JSX | None = None, **_) -> JSX:
        return jsx("div", {}, [image])

    def CardWithImageCallable(image: JSXComponent, **_) -> JSX:
        return jsx("div", {}, [jsx(image, {}, [])])

    def Image(src: str = "example.jpg", alt: str | None = None, **_) -> JSX:
        return jsx("img", {"src": src, "alt": alt}, [])

    html = run_example("str(<Card />)", {"Card": CardWithImageComponent, "Image": Image})
    assert html == "<div></div>"

    with pytest.raises(TypeError):
        run_example("str(<Card />)", {"Card": CardWithImageCallable, "Image": Image})

    html = run_example(
        "str(<Card image={<Image src='example.jpg' />} />)",
        {"Card": CardWithImageComponent, "Image": Image},
    )
    assert (
        html
        == """\
<div>
    <img src="example.jpg" />
</div>"""
    )

    html = run_example("str(<Card image={Image} />)", {"Card": CardWithImageCallable, "Image": Image})
    assert (
        html
        == """\
<div>
    <img src="example.jpg" />
</div>"""
    )

    with pytest.raises(TypeError) as excinfo:
        run_example(
            "str(<Card image={<Image />} />)",
            {"Card": CardWithImageCallable, "Image": Image},
        )
    assert str(excinfo.value) == "Element type is invalid. Expected a string or a function but got: <Image />"
