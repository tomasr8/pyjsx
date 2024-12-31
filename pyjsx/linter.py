import dataclasses
from collections import defaultdict
from typing import Any

from pyjsx.transpiler import (
    JSXElement,
    JSXExpression,
    JSXFragment,
    JSXNamedAttribute,
    JSXSpreadAttribute,
    Node,
    Parser,
    PythonData,
)


class NodeVisitor:
    def visit(self, node: Node) -> Any:
        method_name = "visit_" + type(node).__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: Node) -> Any:
        for _, value in get_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, Node):
                        self.visit(item)
            elif isinstance(value, Node):
                self.visit(value)


def get_fields(node: Node) -> list[tuple[str, Any]]:
    return [(f.name, getattr(node, f.name)) for f in dataclasses.fields(node)]


class NodeTransformer(NodeVisitor):
    def generic_visit(self, node: Node) -> Node:
        for field, old_value in get_fields(node):
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    if isinstance(value, Node):
                        value = self.visit(value)
                        if value is None:
                            continue
                        if not isinstance(value, Node):
                            new_values.extend(value)
                            continue
                    new_values.append(value)
                old_value[:] = new_values
            elif isinstance(old_value, Node):
                new_node = self.visit(old_value)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
        return node


class Linter(NodeVisitor):
    def __init__(self):
        self.errors = []

    def lint(self, source: str) -> list:
        node = Parser(source).parse()
        self.visit(node)
        return self.errors

    def visit_JSXExpression(self, node: JSXExpression) -> None:
        self.generic_visit(node)
        if not node.children:
            self.errors.append((node, "Empty JSX expression"))

    def visit_JSXElement(self, node: JSXElement) -> None:
        self.generic_visit(node)
        self._check_duplicate_props(node.attributes)
        self._check_self_closing_empty_body(node)

    def visit_JSXNamedAttribute(self, node: JSXNamedAttribute) -> None:
        self.generic_visit(node)
        match node.value:
            case JSXExpression(children=[PythonData(value="True")]):
                self.errors.append((node, "Explicit boolean value can be omitted"))
            case _:
                pass

    def visit_JSXFragment(self, node: JSXFragment) -> None:
        self.generic_visit(node)
        match node.children:
            case []:
                self.errors.append((node, "Empty JSX fragment"))
            case [JSXFragment() | JSXElement()]:
                self.errors.append((node, "Fragment with a single child"))
            case _:
                pass

    def _check_duplicate_props(self, attributes: list[JSXNamedAttribute | JSXSpreadAttribute]) -> None:
        dupes = defaultdict(list)
        for attr in attributes:
            match attr:
                case JSXNamedAttribute(name=name):
                    dupes[name].append(attr)
                case _:
                    pass
        for name, attrs in dupes.items():
            if len(attrs) > 1:
                self.errors.append((attrs, f'Duplicate prop "{name}"'))

    def _check_self_closing_empty_body(self, node: JSXElement) -> None:
        if node.self_closing:
            return

        if not node.children:
            self.errors.append((node, "Empty components can be self-closing"))


def lint(source: str) -> list[tuple[Node, str]]:
    return Linter().lint(source)


def fix(source: str) -> str:
    node = Parser(source).parse()
    node = remove_empty_jsx_expressions(node)
    node = remove_empty_jsx_fragments(node)
    node = remove_fragments_with_single_child(node)
    node = remove_duplicate_props(node)
    node = self_close_empty_components(node)
    node = remove_boolean_prop_value(node)
    return node.unparse()


def remove_empty_jsx_expressions(ast: Node) -> Node:
    class Transformer(NodeTransformer):
        def visit_JSXExpression(self, node: JSXExpression) -> Node | None:
            self.generic_visit(node)
            if not node.children:
                return None
            return node

    return Transformer().visit(ast)


def remove_empty_jsx_fragments(ast: Node) -> Node:
    class Transformer(NodeTransformer):
        def visit_JSXFragment(self, node: JSXFragment) -> Node | None:
            self.generic_visit(node)
            if not node.children:
                return None
            return node

    return Transformer().visit(ast)


def remove_fragments_with_single_child(ast: Node) -> Node:
    class Transformer(NodeTransformer):
        def visit_JSXFragment(self, node: JSXFragment) -> Node:
            self.generic_visit(node)
            match node.children:
                case [JSXFragment() | JSXElement()]:
                    return node.children[0]
                case _:
                    return node

    return Transformer().visit(ast)


def remove_duplicate_props(ast: Node) -> Node:
    class Transformer(NodeTransformer):
        def visit_JSXElement(self, node: JSXElement) -> Node:
            self.generic_visit(node)
            dupes = defaultdict(list)
            for attr in node.attributes:
                match attr:
                    case JSXNamedAttribute(name=name):
                        dupes[name].append(attr)
                    case _:
                        pass
            attributes = [v[0] for v in dupes.values()]
            return dataclasses.replace(node, attributes=attributes)

    return Transformer().visit(ast)


def self_close_empty_components(ast: Node) -> Node:
    class Transformer(NodeTransformer):
        def visit_JSXElement(self, node: JSXElement) -> Node:
            self.generic_visit(node)
            if node.self_closing or node.children:
                return node
            return dataclasses.replace(node, open_token2=None, close_token2=None)

    return Transformer().visit(ast)


def remove_boolean_prop_value(ast: Node) -> Node:
    class Transformer(NodeTransformer):
        def visit_JSXNamedAttribute(self, node: JSXNamedAttribute) -> Node:
            self.generic_visit(node)
            match node.value:
                case JSXExpression(children=[PythonData(value="True")]):
                    return dataclasses.replace(node, value=True)
                case _:
                    return node

    return Transformer().visit(ast)
