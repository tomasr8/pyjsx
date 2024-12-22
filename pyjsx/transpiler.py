from __future__ import annotations

import re
from dataclasses import dataclass
from io import StringIO
from typing import Any, TypeAlias

from pyjsx.elements import is_builtin_element
from pyjsx.source_maps.source_maps import get_end_offset, offset_by, extend_last
from pyjsx.tokenizer import Token, Tokenizer, TokenType


UNESCAPED_QUOTES = re.compile(r'(?<!\\)"')
SourceMap: TypeAlias = dict[int, tuple[int, int, int]]


class ParseError(Exception):
    pass


@dataclass(frozen=True)
class JSXAttributeLiteral:
    value: str
    token: Token

    def transpile(self) -> tuple[str, SourceMap]:
        source_map = {0: (len(self.value), self.token.start, self.token.end)}
        return self.value, source_map

    def __str__(self):
        return self.value


@dataclass(frozen=True)
class JSXNamedAttribute:
    name: str
    value: JSXAttributeLiteral | JSXExpression | JSXElement | JSXFragment
    name_token: Token

    def transpile(self) -> tuple[str, SourceMap]:
        transpiled = f'"{self.name}": '
        source_map = {0: (len(self.name) + 4, self.name_token.start, self.name_token.end)}
        transpiled_value, source_map_value = self.value.transpile()
        transpiled += transpiled_value
        source_map |= offset_by(source_map_value, get_end_offset(source_map))
        return transpiled, source_map


@dataclass(frozen=True)
class JSXSpreadAttribute:
    value: JSXExpression

    def transpile(self) -> tuple[str, SourceMap]:
        return self.value.transpile()  # TODO


@dataclass(frozen=True)
class JSXFragment:
    children: list
    open_token: Token
    close_token: Token

    def transpile(self) -> tuple[str, SourceMap]:
        transpiled = "jsx(jsx.Fragment, {}, ["
        source_map = {0: (23, self.open_token.start, self.open_token.end)}
        for i, child in enumerate(self.children):
            transpiled_child, souce_map_child = child.transpile()
            transpiled += transpiled_child
            if i < len(self.children) - 1:
                transpiled += ", "
                # end = get_end_offset(source_map)
                # source_map |= {end: (end+2, self.open_token.start, self.open_token.end)}
                source_map = extend_last(source_map, 2)
            source_map |= offset_by(souce_map_child, get_end_offset(source_map))
        offset = get_end_offset(source_map)
        source_map[offset] = (offset + 2, self.close_token.start, self.close_token.end)
        transpiled += "])"
        return transpiled, source_map

    def __str__(self):
        children = ", ".join(str(child) for child in self.children)
        return f"jsx(jsx.Fragment, {{}}, [{children}])"


@dataclass(frozen=True)
class JSXElement:
    name: str
    attributes: list[JSXNamedAttribute | JSXSpreadAttribute]
    children: list
    open_token: Token
    close_token: Token
    name_token: Token
    open_token2: Token | None = None
    close_token2: Token | None = None

    def transpile(self) -> tuple[str, SourceMap]:
        transpiled = "jsx("
        source_map = {0: (4, self.open_token.start, self.open_token.end)}
        transpiled_name, source_map_name = self.transpile_name()
        transpiled += transpiled_name
        source_map |= offset_by(source_map_name, get_end_offset(source_map))
        transpiled += ", "
        source_map = extend_last(source_map, 2)
        transpiled_attributes, source_map_attributes = self.transpile_attributes()
        transpiled += transpiled_attributes
        source_map |= offset_by(source_map_attributes, get_end_offset(source_map))
        transpiled += ", ["
        source_map = extend_last(source_map, 3)

        for i, child in enumerate(self.children):
            transpiled_child, souce_map_child = child.transpile()
            transpiled += transpiled_child
            if i < len(self.children) - 1:
                transpiled += ", "
                source_map = extend_last(source_map, 2)
            source_map |= offset_by(souce_map_child, get_end_offset(source_map))

        transpiled += "])"
        offset = get_end_offset(source_map)
        source_map[offset] = (offset + 2, self.close_token.start, self.close_token.end)
        return transpiled, source_map

    def transpile_name(self) -> tuple[str, SourceMap]:
        if is_builtin_element(self.name):
            return f'"{self.name}"', {0: (len(self.name) + 2, self.name_token.start, self.name_token.end)}
        return self.name, {0: (len(self.name), self.name_token.start, self.name_token.end)}

    def transpile_attributes(self) -> tuple[str, SourceMap]:
        if not self.attributes:
            return "{}", {}
        transpiled = "{"
        source_map = {0: (1, self.attributes[0].name_token.start, self.attributes[0].name_token.end)}

        for i, attr in enumerate(self.attributes):
            transpiled_attr, source_map_attr = attr.transpile()
            transpiled += transpiled_attr
            if i < len(self.attributes) - 1:
                transpiled += ", "
                source_map = extend_last(source_map, 2)
            source_map |= offset_by(source_map_attr, get_end_offset(source_map))

        transpiled += "}"
        source_map = extend_last(source_map, 1)
        return transpiled, source_map

    def __str__(self):
        condensed = []
        curr = {}
        for attr in self.attributes:
            match attr:
                case JSXNamedAttribute(name, value):
                    curr[name] = value
                case JSXSpreadAttribute(value):
                    if curr:
                        condensed.append(curr)
                        curr = {}
                    condensed.append(value)
                case _:
                    msg = "Invalid attribute"
                    raise ParseError(msg)
        if curr:
            condensed.append(curr)

        condensed = condensed or [{}]
        attributes = " | ".join(self.sringify_attribute_dict(attrs) for attrs in condensed)
        children = ", ".join(str(child) for child in self.children)
        tag = f'"{self.name}"' if is_builtin_element(self.name) else self.name
        return f"jsx({tag}, {attributes}, [{children}])"

    def sringify_attribute_dict(self, attrs: dict[str, Any]) -> str:
        if isinstance(attrs, JSXExpression | JSXElement | JSXFragment):
            return f"({attrs})"
        if not attrs:
            return "{}"
        kvs = ", ".join(f"'{k}': {v}" for k, v in attrs.items())
        return f"{{{kvs}}}"


@dataclass(frozen=True)
class JSXText:
    value: str
    token: Token

    def transpile(self) -> tuple[str, SourceMap]:
        transpiled = str(self)
        source_map = {0: (len(transpiled), self.token.start, self.token.end)}
        return transpiled, source_map

    def __str__(self):
        value = re.sub(UNESCAPED_QUOTES, '\\"', self.value)
        return f'"{value}"'


@dataclass(frozen=True)
class JSXExpression:
    children: list
    open_token: Token
    close_token: Token

    def transpile(self) -> tuple[str, SourceMap]:
        transpiled = ""
        source_map = {}
        for child in self.children:
            transpiled_child, souce_map_child = child.transpile()
            transpiled += transpiled_child
            source_map |= offset_by(souce_map_child, get_end_offset(source_map))

        return transpiled, source_map

    def __str__(self):
        return "".join(str(child) for child in self.children)


@dataclass(frozen=True)
class PythonData:
    value: str
    start_token: Token
    end_token: Token

    def transpile(self) -> tuple[str, SourceMap]:
        source_map = {0: (len(self.value), self.start_token.start, self.end_token.end)}
        return str(self), source_map

    def __str__(self):
        return self.value


@dataclass(frozen=True)
class PyJSXProgram:
    children: list[PythonData | JSXElement | JSXFragment]

    def transpile(self) -> tuple[str, SourceMap]:
        transpiled = ""
        source_map = {}
        for child in self.children:
            transpiled_child, souce_map_child = child.transpile()
            transpiled += transpiled_child
            source_map |= offset_by(souce_map_child, get_end_offset(source_map))

        return transpiled, source_map

    def __str__(self):
        return "".join(str(child) for child in self.children)


class TokenQueue:
    def __init__(self, tokens: list[Token], offset: int = 0, raw: str = ""):
        self.tokens = list(tokens)
        self.raw = raw
        self.curr = offset

    def peek(self) -> Token | None:
        if self.curr >= len(self.tokens):
            return None
        return self.tokens[self.curr]

    def peek2(self) -> Token | None:
        if self.curr + 1 >= len(self.tokens):
            return None
        return self.tokens[self.curr + 1]

    def peek_type(self, typ: TokenType, value: str | None = None) -> Token | None:
        token = self.peek()
        if token and token.type == typ and (not value or token.value == value):
            return token
        return None

    def peek_type2(self, typ: TokenType, value: str | None = None) -> Token | None:
        token = self.peek2()
        if token and token.type == typ and (not value or token.value == value):
            return token
        return None

    def pop(self, typ: TokenType | None = None) -> Token:
        if self.curr >= len(self.tokens):
            msg = "No more tokens"
            raise ParseError(msg)

        self.curr += 1
        token = self.tokens[self.curr - 1]
        if typ and token.type != typ:
            msg = f"Expected {typ}, got {token.type}, {token.value}"
            raise ParseError(msg)
        return token

    def pop_type(self, typ: TokenType) -> Token:
        return self.pop(typ=typ)


def parse_jsx(queue: TokenQueue) -> JSXElement | JSXFragment:
    if queue.peek_type(TokenType.JSX_OPEN):
        return parse_jsx_element(queue)
    if queue.peek_type(TokenType.JSX_FRAGMENT_OPEN):
        return parse_jsx_fragment(queue)
    msg = f"Unexpected token {queue.peek()}"
    raise ParseError(msg)


def parse_jsx_element(queue: TokenQueue) -> JSXElement:
    open_token = queue.pop_type(TokenType.JSX_OPEN)
    name_token = queue.pop_type(TokenType.ELEMENT_NAME)
    name = name_token.value
    attributes = []
    if not queue.peek_type(TokenType.JSX_CLOSE) and not queue.peek_type(TokenType.JSX_SLASH_CLOSE):
        attributes = parse_jsx_attributes(queue)
    if queue.peek_type(TokenType.JSX_SLASH_CLOSE):
        close_token = queue.pop()
        return JSXElement(name, attributes, [], open_token=open_token, close_token=close_token, name_token=name_token)

    close_token = queue.pop_type(TokenType.JSX_CLOSE)
    children = []
    if not queue.peek_type(TokenType.JSX_SLASH_OPEN):
        children = parse_jsx_children(queue)
    open_token2 = queue.pop_type(TokenType.JSX_SLASH_OPEN)
    closing_tag = queue.pop_type(TokenType.ELEMENT_NAME).value
    if closing_tag != name:
        msg = f"Expected closing tag {name}, got {closing_tag}"
        raise ParseError(msg)
    close_token2 = queue.pop_type(TokenType.JSX_CLOSE)
    return JSXElement(name, attributes, children, open_token, close_token, name_token, open_token2, close_token2)


def parse_jsx_fragment(queue: TokenQueue) -> JSXFragment:
    open = queue.pop_type(TokenType.JSX_FRAGMENT_OPEN)
    children = []
    if not queue.peek_type(TokenType.JSX_FRAGMENT_CLOSE):
        children = parse_jsx_children(queue)
    close = queue.pop_type(TokenType.JSX_FRAGMENT_CLOSE)
    return JSXFragment(children, open_token=open, close_token=close)


def parse_jsx_children(queue: TokenQueue) -> list:
    children = []
    while not queue.peek_type(TokenType.JSX_SLASH_OPEN) and not queue.peek_type(TokenType.JSX_FRAGMENT_CLOSE):
        if queue.peek_type(TokenType.JSX_OPEN):
            children.append(parse_jsx_element(queue))
        elif queue.peek_type(TokenType.JSX_FRAGMENT_OPEN):
            children.append(parse_jsx_fragment(queue))
        elif queue.peek_type(TokenType.JSX_OPEN_BRACE):
            children.append(parse_python_expression(queue))
        else:
            jsx_text = parse_jsx_text(queue)
            if jsx_text:
                children.append(jsx_text)
    return children


def parse_jsx_text(queue: TokenQueue) -> JSXText | None:
    tok = queue.pop_type(TokenType.JSX_TEXT)
    lines = tok.value.split("\n")
    lines = [line.strip() for line in lines]
    lines = [line for line in lines if line]
    if not lines:
        return None
    value = " ".join(lines)
    return JSXText(value, token=tok)


def parse_jsx_attributes(queue: TokenQueue) -> list[JSXNamedAttribute | JSXSpreadAttribute]:
    attributes = []
    while not queue.peek_type(TokenType.JSX_CLOSE) and not queue.peek_type(TokenType.JSX_SLASH_CLOSE):
        if queue.peek_type(TokenType.ATTRIBUTE):
            attributes.append(parse_named_attribute(queue))
        elif queue.peek_type(TokenType.JSX_OPEN_BRACE) and queue.peek_type2(TokenType.JSX_SPREAD):
            attributes.append(parse_jsx_spread_attribute(queue))
        else:
            msg = f"Unexpected token while parsing JSX attributes: {queue.peek()}"
            raise ParseError(msg)
    return attributes


def parse_named_attribute(queue: TokenQueue) -> JSXNamedAttribute:
    name_token = queue.pop_type(TokenType.ATTRIBUTE)
    name = name_token.value
    if queue.peek_type(TokenType.OP, value="="):
        queue.pop()
        value = parse_jsx_attribute_value(queue)
    else:
        value = JSXAttributeLiteral(value="True", token=name_token)
    return JSXNamedAttribute(name, value, name_token=name_token)


def parse_jsx_spread_attribute(queue: TokenQueue) -> JSXSpreadAttribute:
    return JSXSpreadAttribute(parse_python_expression(queue, pop_spread=True))


def parse_jsx_attribute_value(queue: TokenQueue) -> JSXAttributeLiteral | JSXExpression | JSXElement | JSXFragment:
    if queue.peek_type(TokenType.ATTRIBUTE_VALUE):
        token = queue.pop()
        return JSXAttributeLiteral(token.value, token)
    if queue.peek_type(TokenType.JSX_OPEN_BRACE):
        return parse_python_expression(queue)
    if queue.peek_type(TokenType.JSX_OPEN):
        return parse_jsx_element(queue)
    if queue.peek_type(TokenType.JSX_FRAGMENT_OPEN):
        return parse_jsx_fragment(queue)
    msg = f"Unexpected token while parsing JSX attribute value: {queue.peek()}"
    raise ParseError(msg)


def parse_python_expression(queue: TokenQueue, *, pop_spread: bool = False) -> JSXExpression:
    open = queue.pop_type(TokenType.JSX_OPEN_BRACE)
    if pop_spread:
        queue.pop_type(TokenType.JSX_SPREAD)
    children = []
    while not queue.peek_type(TokenType.JSX_CLOSE_BRACE):
        if queue.peek_type(TokenType.JSX_OPEN) or queue.peek_type(TokenType.JSX_FRAGMENT_OPEN):
            children.append(parse_jsx(queue))
        else:
            children.append(queue.pop().value)
    close = queue.pop_type(TokenType.JSX_CLOSE_BRACE)
    return JSXExpression(children, open_token=open, close_token=close)


def _parse(source: str, fn):
    tokenizer = Tokenizer(source)
    tokens = list(tokenizer.tokenize())
    queue = TokenQueue(tokens)
    return fn(queue)


class Parser:
    def __init__(self, source: str):
        self.source = source
        self.tokenizer = Tokenizer(source)
        self.curr = 0

    def parse(self) -> PyJSXProgram:
        children = []
        python_tokens = []
        tokens = list(self.tokenizer.tokenize())
        tok_len = len(tokens)
        while self.curr < tok_len:
            token = tokens[self.curr]
            if token.type not in {TokenType.JSX_OPEN, TokenType.JSX_FRAGMENT_OPEN}:
                python_tokens.append(token)
                self.curr += 1
            else:
                if python_tokens:
                    children.append(
                        PythonData(
                            "".join(token.value for token in python_tokens),
                            python_tokens[0],
                            python_tokens[-1],
                        )
                    )
                    python_tokens = []
                queue = TokenQueue(tokens, self.curr, raw=self.source)
                jsx = parse_jsx(queue)
                children.append(jsx)
                self.curr = queue.curr
        if python_tokens:
            children.append(
                PythonData(
                    "".join(token.value for token in python_tokens),
                    python_tokens[0],
                    python_tokens[-1],
                )
            )
            python_tokens = []
        return PyJSXProgram(children)


class Transpiler:
    def __init__(self, ast: PyJSXProgram):
        self.ast = ast
        self.output = StringIO()
        self.curr_map = None
        self.source_map = {}

    def transpile(self) -> str:
        start_offset = 0
        for ch in self.ast.children:
            # sm = ch.source_map(start_offset)
            # self.source_map |= sm
            # start_offset = get_end_offset(sm)
            self.output.write(str(ch))

        return self.output.getvalue()


def transpile(source: str) -> str:
    ast = Parser(source).parse()
    transpiler = Transpiler(ast)
    return transpiler.transpile()
