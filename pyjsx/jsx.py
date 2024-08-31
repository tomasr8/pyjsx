from __future__ import annotations

from typing import Any, Protocol

from pyjsx.elements import is_void_element
from pyjsx.util import flatten, indent


__all__ = ["jsx"]


class JSXComponent(Protocol):
    __name__: str

    def __call__(self, *, children: list[JSX], **rest: Any) -> JSX: ...


class JSXFragment(Protocol):
    __name__: str

    def __call__(self, *, children: list[JSX], **rest: Any) -> list[JSX]: ...


class JSXElement:
    def __init__(
        self,
        tag: str | JSXComponent | JSXFragment,
        props: dict[str, Any],
        children: list[JSX],
    ):
        self.tag = tag
        self.props = props
        self.children = children

    def __repr__(self):
        tag = self.tag if isinstance(self.tag, str) else self.tag.__name__
        return f"<{tag} />"

    def __str__(self):
        match self.tag:
            case str():
                return self.convert_builtin(self.tag)
            case _:
                return self.convert_component(self.tag)

    def convert_prop(self, key: str, value: Any) -> str:
        if isinstance(value, bool):
            return key if value else ""
        value = str(value).replace('"', "&quot;")
        return f'{key}="{value}"'

    def convert_props(self, props: dict[str, Any]) -> str:
        not_none = {k: v for k, v in props.items() if v is not None}
        formatted = " ".join([self.convert_prop(k, v) for k, v in not_none.items()])
        if formatted:
            return f" {formatted}"
        return ""

    def convert_builtin(self, tag: str) -> str:
        props = self.convert_props(self.props)
        children = [child for child in flatten(self.children) if child is not None]
        if not children:
            if is_void_element(tag):
                return f"<{tag}{props} />"
            return f"<{tag}{props}></{tag}>"
        children = flatten(str(child) for child in children)
        children_formatted = "\n".join(indent(child) for child in children)
        return f"<{tag}{props}>\n{children_formatted}\n</{tag}>"

    def convert_component(self, tag: JSXComponent | JSXFragment) -> str:
        rendered = tag(**self.props, children=self.children)
        match rendered:
            case None:
                return ""
            case tuple() | list():
                return "\n".join(str(child) for child in rendered)
            case _:
                return str(rendered)


class _JSX:
    def __call__(
        self,
        tag: str | JSXComponent | JSXFragment,
        props: dict[str, Any] | None = None,
        children: list[Any] | None = None,
    ) -> JSXElement:
        if not isinstance(tag, str) and not callable(tag):
            msg = f"Element type is invalid. Expected a string or a function but got: {tag!r}"
            raise TypeError(msg)
        if props is None:
            props = {}
        if children is None:
            children = []
        if (style := props.get("style")) and isinstance(style, dict):
            props["style"] = "; ".join([f"{k}: {v}" for k, v in style.items()])
        return JSXElement(tag, props, children)

    def Fragment(self, *, children: list[Any], **_: Any) -> list[Any]:
        return children


jsx = _JSX()
type JSX = JSXElement | str
