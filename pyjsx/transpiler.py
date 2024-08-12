from __future__ import annotations

import re
from dataclasses import dataclass
from io import StringIO
from typing import Any

from pyjsx.elements import is_builtin_element
from pyjsx.tokenizer import Token, Tokenizer, TokenType


UNESCAPED_QUOTES = re.compile(r'(?<!\\)"')


class ParseError(Exception):
    pass


@dataclass
class JSXNamedAttribute:
    name: str
    value: str | JSXExpression | JSXElement | JSXFragment


@dataclass
class JSXSpreadAttribute:
    value: JSXExpression


@dataclass
class JSXFragment:
    children: list

    def __str__(self):
        children = ", ".join(str(child) for child in self.children)
        return f"jsx(jsx.Fragment, {{}}, [{children}])"


@dataclass
class JSXElement:
    name: str
    attributes: list[JSXNamedAttribute | JSXSpreadAttribute]
    children: list

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
        attributes = " | ".join(sringify_attribute_dict(attrs) for attrs in condensed)
        children = ", ".join(str(child) for child in self.children)
        tag = f'"{self.name}"' if is_builtin_element(self.name) else self.name
        return f"jsx({tag}, {attributes}, [{children}])"


def sringify_attribute_dict(attrs: dict[str, Any]) -> str:
    if isinstance(attrs, JSXExpression | JSXElement | JSXFragment):
        return f"({attrs})"
    if not attrs:
        return "{}"
    kvs = ", ".join(f"'{k}': {v}" for k, v in attrs.items())
    return f"{{{kvs}}}"


@dataclass
class JSXText:
    value: str

    def __str__(self):
        value = re.sub(UNESCAPED_QUOTES, '\\"', self.value)
        return f'"{value}"'


@dataclass
class JSXExpression:
    children: list

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
    queue.pop_type(TokenType.JSX_OPEN)
    name = queue.pop_type(TokenType.ELEMENT_NAME).value
    attributes = []
    if not queue.peek_type(TokenType.JSX_CLOSE) and not queue.peek_type(TokenType.JSX_SLASH_CLOSE):
        attributes = parse_jsx_attributes(queue)
    if queue.peek_type(TokenType.JSX_SLASH_CLOSE):
        queue.pop()
        return JSXElement(name, attributes, [])

    queue.pop_type(TokenType.JSX_CLOSE)
    children = []
    if not queue.peek_type(TokenType.JSX_SLASH_OPEN):
        children = parse_jsx_children(queue)
    queue.pop_type(TokenType.JSX_SLASH_OPEN)
    closing_tag = queue.pop_type(TokenType.ELEMENT_NAME).value
    if closing_tag != name:
        msg = f"Expected closing tag {name}, got {closing_tag}"
        raise ParseError(msg)
    queue.pop_type(TokenType.JSX_CLOSE)
    return JSXElement(name, attributes, children)


def parse_jsx_fragment(queue: TokenQueue) -> JSXFragment:
    queue.pop_type(TokenType.JSX_FRAGMENT_OPEN)
    children = []
    if not queue.peek_type(TokenType.JSX_FRAGMENT_CLOSE):
        children = parse_jsx_children(queue)
    queue.pop_type(TokenType.JSX_FRAGMENT_CLOSE)
    return JSXFragment(children)


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
    value = queue.pop_type(TokenType.JSX_TEXT).value
    lines = value.split("\n")
    lines = [line.strip() for line in lines]
    lines = [line for line in lines if line]
    if not lines:
        return None
    value = " ".join(lines)
    return JSXText(value)


def parse_jsx_attributes(queue: TokenQueue) -> list:
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
    name = queue.pop_type(TokenType.ATTRIBUTE).value
    if queue.peek_type(TokenType.OP, value="="):
        queue.pop()
        value = parse_jsx_attribute_value(queue)
    else:
        value = "True"
    return JSXNamedAttribute(name, value)


def parse_jsx_spread_attribute(queue: TokenQueue) -> JSXSpreadAttribute:
    return JSXSpreadAttribute(parse_python_expression(queue, pop_spread=True))


def parse_jsx_attribute_value(queue: TokenQueue) -> str | JSXExpression | JSXElement | JSXFragment:
    if queue.peek_type(TokenType.ATTRIBUTE_VALUE):
        return queue.pop().value
    if queue.peek_type(TokenType.JSX_OPEN_BRACE):
        return parse_python_expression(queue)
    if queue.peek_type(TokenType.JSX_OPEN):
        return parse_jsx_element(queue)
    if queue.peek_type(TokenType.JSX_FRAGMENT_OPEN):
        return parse_jsx_fragment(queue)
    msg = f"Unexpected token while parsing JSX attribute value: {queue.peek()}"
    raise ParseError(msg)


def parse_python_expression(queue: TokenQueue, *, pop_spread: bool = False) -> JSXExpression:
    queue.pop_type(TokenType.JSX_OPEN_BRACE)
    if pop_spread:
        queue.pop_type(TokenType.JSX_SPREAD)
    children = []
    while not queue.peek_type(TokenType.JSX_CLOSE_BRACE):
        if queue.peek_type(TokenType.JSX_OPEN) or queue.peek_type(TokenType.JSX_FRAGMENT_OPEN):
            children.append(parse_jsx(queue))
        else:
            children.append(queue.pop().value)
    queue.pop_type(TokenType.JSX_CLOSE_BRACE)
    return JSXExpression(children)


class Transpiler:
    def __init__(self, source: str):
        self.source = source
        self.tokenizer = Tokenizer(source)
        self.output = StringIO()
        self.curr = 0

    def transpile(self) -> str:
        tokens = list(self.tokenizer.tokenize())
        while self.curr < len(tokens):
            if tokens[self.curr].type not in {TokenType.JSX_OPEN, TokenType.JSX_FRAGMENT_OPEN}:
                self.output.write(tokens[self.curr].value)
                self.curr += 1
            else:
                queue = TokenQueue(tokens, self.curr, raw=self.source)
                jsx = parse_jsx(queue)
                self.curr = queue.curr
                self.output.write(str(jsx))
        return self.output.getvalue()


def transpile(source: str) -> str:
    transpiler = Transpiler(source)
    return transpiler.transpile()
