import pytest

from pyjsx import JSX, JSXComponent, jsx, transpile


def run_example(source: str, _locals=None):
    py_code = transpile(source)
    return eval(py_code, {"jsx": jsx}, _locals)  # noqa: S307


def test_passing_jsx_as_props():
    def CardWithImageComponent(image: JSX | None = None, **_):
        return jsx("div", {}, [image])

    def CardWithImageCallable(image: JSXComponent, **_):
        return jsx("div", {}, [jsx(image, {}, [])])

    def Image(src="example.jpg", alt=None, **_):
        return jsx("img", {"src": src, "alt": alt}, [])

    html = run_example(
        "str(<Card />)", {"Card": CardWithImageComponent, "Image": Image}
    )
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

    html = run_example(
        "str(<Card image={Image} />)", {"Card": CardWithImageCallable, "Image": Image}
    )
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
    assert (
        str(excinfo.value)
        == "Element type is invalid. Expected a string or a function but got: <Image />"
    )
