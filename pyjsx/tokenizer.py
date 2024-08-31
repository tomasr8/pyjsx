import re
from collections.abc import Generator
from dataclasses import dataclass
from enum import StrEnum

from pyjsx.util import get_line_number_offset, highlight_line


ELEMENT_NAME = re.compile(r"^[_a-zA-Z]\w*(?:\.[_a-zA-Z]\w*)*")
ATTRIBUTE_NAME = re.compile(r"^[^\s='\"<>{}]+")
ATTRIBUTE_STRING_VALUE = re.compile(r"^(?:'[^']*')|(?:\"[^\"]*\")")
JSX_TEXT = re.compile(r"^[^<>\{\}]+")
WS = re.compile(r"^\s+")

COMMENT = re.compile(r"^#[^\n]*", re.UNICODE)
SINGLE_LINE_STRING = re.compile(r"^[rRbBuU]*('[^']*')|(\"[^\"]*\")", re.UNICODE)
EXPR_KEYWORDS = re.compile(r"^(else|yield|return)", re.UNICODE)
NAME = re.compile(r"^[a-zA-Z_]\w*", re.UNICODE)
MULTI_LINE_STRING_START = re.compile(r"^[rRbBuU]*('''|\"\"\")", re.UNICODE)
SINGLE_LINE_STRING_START = re.compile(r"^[rRbBuU]*('|\")", re.UNICODE)
FSTRING_START = re.compile(r"^[rRbBuU]*(?:f|F)[rRbBuU]*('''|\"\"\"|'|\")", re.UNICODE)
FSTRING_MIDDLE = re.compile(r"^[^{}]+", re.UNICODE)
JSX_KEYWORDS = re.compile(r"^(return|yield|else)")


class TokenType(StrEnum):
    OP = "OP"
    ELEMENT_NAME = "ELEMENT_NAME"
    NAME = "NAME"
    JSX_OPEN = "JSX_OPEN"
    JSX_SLASH_OPEN = "JSX_SLASH_OPEN"
    JSX_CLOSE = "JSX_CLOSE"
    JSX_SLASH_CLOSE = "JSX_SLASH_CLOSE"
    JSX_FRAGMENT_OPEN = "JSX_FRAGMENT_OPEN"
    JSX_FRAGMENT_CLOSE = "JSX_FRAGMENT_CLOSE"
    JSX_SPREAD = "JSX_SPREAD"
    JSX_TEXT = "JSX_TEXT"
    JSX_OPEN_BRACE = "JSX_OPEN_BRACE"
    JSX_CLOSE_BRACE = "JSX_CLOSE_BRACE"
    ATTRIBUTE = "ATTRIBUTE"
    ATTRIBUTE_VALUE = "ATTRIBUTE_VALUE"
    WS = "WS"
    COMMENT = "COMMENT"
    SINGLE_LINE_STRING = "SINGLE_LINE_STRING"
    MULTI_LINE_STRING = "MULTI_LINE_STRING"
    FSTRING_START = "FSTRING_START"
    FSTRING_MIDDLE = "FSTRING_MIDDLE"
    FSTRING_END = "FSTRING_END"
    ANY = "ANY"

    def __repr__(self):
        return self.value


@dataclass
class Token:
    type: TokenType
    value: str
    start: int
    end: int


@dataclass
class JSXMode:
    angle_brackets: int = 0
    is_inside_open_tag: bool = False
    is_inside_closing_tag: bool = False
    expects_element_name: bool = False
    expects_spread: bool = False
    expects_attribute_value: bool = False


@dataclass
class PYMode:
    curly_brackets: int = 0
    inside_jsx: bool = False
    inside_fstring: bool = False
    prev_token: str | None = None


@dataclass
class FStringMode:
    start: str = ""


class TokenizerError(Exception):
    pass


def make_error_message(msg: str, source: str, start: int, end: int) -> str:
    line_number, offset = get_line_number_offset(source, start)
    highlighted = highlight_line(source, start, end)

    return f"Error at line {line_number}:\n{highlighted}\n{msg}"


# Yes, the code is pretty bad, but I didn't feel like refactoring it..
class Tokenizer:
    def __init__(self, source: str, curr: int = 0):
        self.source = source
        self.curr = curr
        self.modes: list[PYMode | JSXMode | FStringMode] = [PYMode()]

    @property
    def mode(self) -> PYMode | JSXMode | FStringMode:
        return self.modes[-1]

    def tokenize(self) -> Generator[Token, None, None]:
        while self.curr < len(self.source):
            if isinstance(self.mode, PYMode):
                yield from self.tokenize_py()
            elif isinstance(self.mode, JSXMode):
                yield from self.tokenize_jsx()
                if isinstance(self.mode, JSXMode) and self.mode.angle_brackets == 0:
                    self.modes.pop()
            else:
                yield from self.tokenize_fstring()

    def tokenize_jsx(self) -> Generator[Token, None, None]:  # noqa: C901, PLR0912, PLR0915
        assert isinstance(self.mode, JSXMode)

        if self.source[self.curr : self.curr + 3] == "</>":
            self.mode.angle_brackets -= 1
            yield Token(
                TokenType.JSX_FRAGMENT_CLOSE,
                self.source[self.curr : self.curr + 3],
                self.curr,
                self.curr + 3,
            )
            self.curr += 3
        elif self.source[self.curr : self.curr + 2] == "<>":
            self.mode.angle_brackets += 1
            yield Token(
                TokenType.JSX_FRAGMENT_OPEN,
                self.source[self.curr : self.curr + 2],
                self.curr,
                self.curr + 2,
            )
            self.curr += 2
        elif self.source[self.curr : self.curr + 2] == "</":
            self.mode.is_inside_closing_tag = True
            self.mode.expects_element_name = True
            yield Token(
                TokenType.JSX_SLASH_OPEN,
                self.source[self.curr : self.curr + 2],
                self.curr,
                self.curr + 2,
            )
            self.curr += 2
        elif self.source[self.curr : self.curr + 2] == "/>":
            self.mode.is_inside_open_tag = False
            self.mode.angle_brackets -= 1
            yield Token(TokenType.JSX_SLASH_CLOSE, self.source[self.curr : self.curr + 2], self.curr, self.curr + 2)
            self.curr += 2
        elif self.source[self.curr] in {"<", ">"}:
            if self.source[self.curr] == "<":
                if self.mode.is_inside_open_tag:
                    self.modes.append(JSXMode(is_inside_open_tag=True, angle_brackets=1, expects_element_name=True))
                else:
                    self.mode.is_inside_open_tag = True
                    self.mode.angle_brackets += 1
                    self.mode.expects_element_name = True
                yield Token(TokenType.JSX_OPEN, self.source[self.curr], self.curr, self.curr + 1)
            elif self.source[self.curr] == ">":
                self.mode.is_inside_open_tag = False
                if self.mode.is_inside_closing_tag:
                    self.mode.is_inside_closing_tag = False
                    self.mode.angle_brackets -= 1
                yield Token(TokenType.JSX_CLOSE, self.source[self.curr], self.curr, self.curr + 1)
            self.curr += 1
        elif self.source[self.curr] == "}":
            yield Token(TokenType.JSX_CLOSE_BRACE, self.source[self.curr], self.curr, self.curr + 1)
            self.curr += 1
        elif self.source[self.curr] == "{":
            yield Token(TokenType.JSX_OPEN_BRACE, self.source[self.curr], self.curr, self.curr + 1)
            self.curr += 1
            if self.source[self.curr : self.curr + 3] == "...":
                yield Token(TokenType.JSX_SPREAD, self.source[self.curr : self.curr + 3], self.curr, self.curr + 3)
                self.curr += 3
            self.modes.append(PYMode(curly_brackets=1, inside_jsx=True))

        elif self.mode.is_inside_open_tag or self.mode.is_inside_closing_tag:
            if match := WS.match(self.source[self.curr :]):
                self.curr += len(match.group())
            elif self.mode.is_inside_open_tag and self.source[self.curr] == "=":
                yield Token(TokenType.OP, self.source[self.curr], self.curr, self.curr + 1)
                self.curr += 1
            elif self.mode.expects_element_name and (match := ELEMENT_NAME.match(self.source[self.curr :])):
                name = match.group()
                yield Token(TokenType.ELEMENT_NAME, name, self.curr, self.curr + len(name))
                self.curr += len(name)
                self.mode.expects_element_name = False
            elif (
                not self.mode.expects_element_name
                and self.mode.is_inside_open_tag
                and (match := ATTRIBUTE_NAME.match(self.source[self.curr :]))
            ):
                attr = match.group()
                yield Token(TokenType.ATTRIBUTE, attr, self.curr, self.curr + len(attr))
                self.curr += len(attr)
            elif self.mode.is_inside_open_tag and (match := ATTRIBUTE_STRING_VALUE.match(self.source[self.curr :])):
                value = match.group()
                yield Token(TokenType.ATTRIBUTE_VALUE, value, self.curr, self.curr + len(value))
                self.curr += len(value)
        elif match := JSX_TEXT.match(self.source[self.curr :]):
            text = match.group()
            yield Token(TokenType.JSX_TEXT, text, self.curr, self.curr + len(text))
            self.curr += len(text)
        else:
            msg = f"Unexpected token {self.source[self.curr:]}"
            raise TokenizerError(msg)

    def tokenize_py(self) -> Generator[Token, None, None]:  # noqa: C901, PLR0912, PLR0915
        assert isinstance(self.mode, PYMode)
        if match := WS.match(self.source[self.curr :]):
            yield Token(TokenType.WS, match.group(), self.curr, self.curr + len(match.group()))
            self.curr += len(match.group())
        elif match := COMMENT.match(self.source[self.curr :]):
            yield Token(TokenType.COMMENT, match.group(), self.curr, self.curr + len(match.group()))
            self.curr += len(match.group())
            self.mode.prev_token = match.group()
        elif match := MULTI_LINE_STRING_START.match(self.source[self.curr :]):
            start = match.group(1)
            start_index = self.curr
            self.curr += len(match.group())
            string = match.group()
            found = False
            while self.curr < len(self.source):
                if self.source[self.curr : self.curr + 2] == "\\\\":
                    string += "\\\\"
                    self.curr += 2
                elif self.source[self.curr : self.curr + 2] == "\\'":
                    string += "\\'"
                    self.curr += 2
                elif self.source[self.curr : self.curr + 2] == '\\"':
                    string += '\\"'
                    self.curr += 2
                elif self.source[self.curr : self.curr + 3] == start:
                    string += start
                    self.curr += 3
                    found = True
                    break
                else:
                    string += self.source[self.curr]
                    self.curr += 1

            if not found:
                msg = make_error_message(
                    "Unterminated string", self.source, start_index, start_index + len(match.group())
                )
                raise TokenizerError(msg)
            yield Token(TokenType.MULTI_LINE_STRING, string, start_index, self.curr)
            self.mode.prev_token = string
        elif match := SINGLE_LINE_STRING_START.match(self.source[self.curr :]):
            start = match.group(1)
            start_index = self.curr
            self.curr += len(match.group())
            string = match.group()
            found = False
            while self.curr < len(self.source):
                if self.source[self.curr : self.curr + 2] == "\\\\":
                    string += "\\\\"
                    self.curr += 2
                elif self.source[self.curr : self.curr + 2] == "\\'":
                    string += "\\'"
                    self.curr += 2
                elif self.source[self.curr : self.curr + 2] == '\\"':
                    string += '\\"'
                    self.curr += 2
                elif self.source[self.curr] == start:
                    string += start
                    self.curr += 1
                    found = True
                    break
                else:
                    string += self.source[self.curr]
                    self.curr += 1

            if not found:
                msg = make_error_message(
                    "Unterminated string", self.source, start_index, start_index + len(match.group())
                )
                raise TokenizerError(msg)
            yield Token(TokenType.SINGLE_LINE_STRING, string, start_index, self.curr)
            self.mode.prev_token = string
        elif match := FSTRING_START.match(self.source[self.curr :]):
            start = match.group(1)
            start_index = self.curr
            self.curr += len(match.group())
            string = match.group()
            yield Token(TokenType.FSTRING_START, string, start_index, self.curr)
            self.mode.prev_token = string
            self.modes.append(FStringMode(start=start))
        elif self.source[self.curr] in {":", "(", "[", ",", "=", ":=", "->"}:
            yield Token(TokenType.OP, self.source[self.curr], self.curr, self.curr + 1)
            self.mode.prev_token = self.source[self.curr]
            self.curr += 1
        elif self.source[self.curr : self.curr + 2] in {":=", "->"}:
            yield Token(TokenType.OP, self.source[self.curr : self.curr + 2], self.curr, self.curr + 2)
            self.mode.prev_token = self.source[self.curr : self.curr + 2]
            self.curr += 2
        elif match := JSX_KEYWORDS.match(self.source[self.curr :]):
            yield Token(TokenType.ANY, match.group(), self.curr, self.curr + len(match.group()))
            self.curr += len(match.group())
            self.mode.prev_token = match.group()
        elif self.source[self.curr] == "{":
            self.mode.curly_brackets += 1
            yield Token(TokenType.OP, self.source[self.curr], self.curr, self.curr + 1)
            self.mode.prev_token = self.source[self.curr]
            self.curr += 1
        elif self.source[self.curr] == "}":
            self.mode.curly_brackets -= 1
            if (self.mode.inside_jsx or self.mode.inside_fstring) and self.mode.curly_brackets == 0:
                self.modes.pop()
            else:
                yield Token(TokenType.OP, self.source[self.curr], self.curr, self.curr + 1)
                self.mode.prev_token = self.source[self.curr]
                self.curr += 1
        elif self.source[self.curr] == "<":
            if not self.mode.prev_token or self.mode.prev_token in {
                "{",
                ":",
                "(",
                "[",
                ",",
                "=",
                ":=",
                "->",
                "else",
                "yield",
                "return",
            }:
                self.modes.append(JSXMode())
                self.mode.inside_jsx = True
            else:
                yield Token(TokenType.OP, self.source[self.curr], self.curr, self.curr + 1)
                self.mode.prev_token = self.source[self.curr]
                self.curr += 1
        elif match := NAME.match(self.source[self.curr :]):
            yield Token(TokenType.NAME, match.group(), self.curr, self.curr + len(match.group()))
            self.curr += len(match.group())
            self.mode.prev_token = match.group()
        else:
            yield Token(TokenType.ANY, self.source[self.curr], self.curr, self.curr + 1)
            self.mode.prev_token = self.source[self.curr]
            self.curr += 1

    def tokenize_fstring(self) -> Generator[Token, None, None]:
        assert isinstance(self.mode, FStringMode)
        start = self.mode.start
        if self.source[self.curr] == "{":
            yield Token(TokenType.OP, self.source[self.curr], self.curr, self.curr + 1)
            self.curr += 1
            self.modes.append(PYMode(curly_brackets=1, inside_jsx=False, inside_fstring=True))
        elif self.source[self.curr] == "}":
            yield Token(TokenType.OP, self.source[self.curr], self.curr, self.curr + 1)
            self.curr += 1
        elif self.source[self.curr : self.curr + len(start)] == start:
            yield Token(TokenType.FSTRING_END, start, self.curr, self.curr + len(start))
            self.curr += len(start)
            self.modes.pop()
        else:
            middle = ""
            while self.curr < len(self.source):
                if self.source[self.curr : self.curr + 2] == "{{":
                    middle += "{{"
                    self.curr += 2
                elif self.source[self.curr : self.curr + 2] == "}}":
                    middle += "}}"
                    self.curr += 2
                elif (
                    self.source[self.curr] not in {"{", "}"}
                    and self.source[self.curr : self.curr + len(start)] != start
                ):
                    middle += self.source[self.curr]
                    self.curr += 1
                else:
                    break
            if not middle:
                msg = f"Unexpected token {self.source[self.curr:]}"
                raise TokenizerError(msg)
            yield Token(TokenType.FSTRING_MIDDLE, middle, self.curr, self.curr + len(middle))
