from collections.abc import Callable
from typing import Any, Self

from pyjsx.elements import is_void_element
from pyjsx.util import flatten, indent


__all__ = ["jsx"]


type JSXComponent = Callable[[dict[str, Any]], Any]


class _JSXElement:
    def __init__(self, tag: str | JSXComponent, props: dict[str, Any], children: list[str | Self]):
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
        value = value.replace('"', "&quot;")
        return f'{key}="{value}"'

    def convert_props(self, props: dict[str, Any]) -> str:
        formatted = " ".join([self.convert_prop(k, v) for k, v in props.items()])
        if formatted:
            return f" {formatted}"
        return ""

    def convert_builtin(self, tag: str) -> str:
        props = self.convert_props(self.props)
        if not self.children:
            if is_void_element(tag):
                return f"<{tag}{props} />"
            return f"<{tag}{props}></{tag}>"
        children = flatten(self.children)
        children = flatten(str(child) for child in children)
        children_formatted = "\n".join(indent(child) for child in children)
        return f"<{tag}{props}>\n{children_formatted}\n</{tag}>"

    def convert_component(self, tag: JSXComponent) -> str:
        rendered = tag({**self.props, "children": self.children})
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
        tag: str | JSXComponent,
        props: dict[str, Any] | None = None,
        children: list[str | _JSXElement] | None = None,
    ) -> _JSXElement:
        if props is None:
            props = {}
        if children is None:
            children = []
        if (style := props.get("style")) and isinstance(style, dict):
            props["style"] = "; ".join([f"{k}: {v}" for k, v in style.items()])
        return _JSXElement(tag, props, children)

    def Fragment(self, props: dict[str, Any]) -> _JSXElement:
        return props["children"]


jsx = _JSX()
type JSX = _JSXElement
