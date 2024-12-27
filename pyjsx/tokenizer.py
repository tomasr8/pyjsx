import os
import re
import sys
from collections.abc import Generator
from dataclasses import dataclass

from pyjsx.util import get_line_number_offset, highlight_line


if sys.version_info >= (3, 11):
    from enum import StrEnum  # pyright: ignore[reportAssignmentType]
else:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


ELEMENT_NAME = re.compile(r"^[_a-zA-Z]\w*(?:\.[_a-zA-Z]\w*)*")
ATTRIBUTE_NAME = re.compile(r"^[^\s='\"<>{}]+")
ATTRIBUTE_STRING_VALUE = re.compile(r"^(?:'[^']*')|(?:\"[^\"]*\")")
JSX_TEXT = re.compile(r"^[^<>\{\}]+")
NL = re.compile(r"\r?\n")
WS = re.compile(r"^\s+")

COMMENT = re.compile(r"^#[^\n]*", re.UNICODE)
# JSX_COMMENT = re.compile(r"^<!--[^]*-->", re.UNICODE)
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
    JSX_COMMENT = "JSX_COMMENT"
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


@dataclass(frozen=True)
class SourceLocation:
    offset: int
    line: int  # 1-based index
    column: int  # 0-based offset in the line


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str
    start: int
    end: int
    # _start: SourceLocation | None = None
    # _end: SourceLocation | None = None


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
    def __init__(self, source: str):
        self.source = source
        self.curr = 0
        self.line = 1
        self.column = 0
        self.modes: list[PYMode | JSXMode | FStringMode] = [PYMode()]

    @property
    def mode(self) -> PYMode | JSXMode | FStringMode:
        return self.modes[-1]

    def advance(self, n: int) -> None:
        segment = self.source[self.curr : self.curr + n]
        line_count = segment.count(os.linesep)
        self.curr += n
        if line_count == 0:
            self.column += n
        else:
            self.line += line_count
            index = segment.rfind(os.linesep)
            self.column = len(segment) - index - len(os.linesep)

    def make_token(
        self,
        token_type: TokenType,
        length: int | None = None,
        *,
        value: str | None = None,
        start: int | None = None,
        end: int | None = None,
    ) -> Token:
        if value is None:
            value = self.source[self.curr : self.curr + length]
        if start is None:
            start = self.curr
        if end is None:
            end = self.curr + length
        return Token(token_type, value, start, end)

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
            yield self.make_token(TokenType.JSX_FRAGMENT_CLOSE, 3)
            self.advance(3)
        elif self.source[self.curr : self.curr + 2] == "<>":
            self.mode.angle_brackets += 1
            yield self.make_token(TokenType.JSX_FRAGMENT_OPEN, 2)
            self.advance(2)
        elif self.source[self.curr : self.curr + 2] == "</":
            self.mode.is_inside_closing_tag = True
            self.mode.expects_element_name = True
            yield self.make_token(TokenType.JSX_SLASH_OPEN, 2)
            self.advance(2)
        elif self.source[self.curr : self.curr + 2] == "/>":
            self.mode.is_inside_open_tag = False
            self.mode.angle_brackets -= 1
            yield self.make_token(TokenType.JSX_SLASH_CLOSE, 2)
            self.advance(2)
        elif self.source[self.curr: self.curr + 3] == "{/*":
            start_index = self.curr
            self.advance(3)
            found = False
            value = ""
            while self.curr < len(self.source):
                if self.source[self.curr : self.curr + 3] == "*/}":
                    found = True
                    self.advance(3)
                    break
                value += self.source[self.curr]
                self.advance(1)
            if not found:
                msg = make_error_message("Unterminated comment", self.source, start_index, self.curr)
                raise TokenizerError(msg)
            yield self.make_token(TokenType.JSX_COMMENT, value=value, start=start_index, end=self.curr)
        elif self.source[self.curr] in {"<", ">"}:
            if self.source[self.curr] == "<":
                if self.mode.is_inside_open_tag:
                    self.modes.append(JSXMode(is_inside_open_tag=True, angle_brackets=1, expects_element_name=True))
                else:
                    self.mode.is_inside_open_tag = True
                    self.mode.angle_brackets += 1
                    self.mode.expects_element_name = True
                yield self.make_token(TokenType.JSX_OPEN, 1)
            elif self.source[self.curr] == ">":
                self.mode.is_inside_open_tag = False
                if self.mode.is_inside_closing_tag:
                    self.mode.is_inside_closing_tag = False
                    self.mode.angle_brackets -= 1
                yield self.make_token(TokenType.JSX_CLOSE, 1)
            self.advance(1)
        elif self.source[self.curr] == "}":
            yield self.make_token(TokenType.JSX_CLOSE_BRACE, 1)
            self.advance(1)
        elif self.source[self.curr] == "{":
            yield self.make_token(TokenType.JSX_OPEN_BRACE, 1)
            self.advance(1)
            if self.source[self.curr : self.curr + 3] == "...":
                yield self.make_token(TokenType.JSX_SPREAD, 3)
                self.advance(3)
            self.modes.append(PYMode(curly_brackets=1, inside_jsx=True))

        elif self.mode.is_inside_open_tag or self.mode.is_inside_closing_tag:
            if match := WS.match(self.source[self.curr :]):
                self.advance(len(match.group()))
            elif self.mode.is_inside_open_tag and self.source[self.curr] == "=":
                yield self.make_token(TokenType.OP, 1)
                self.advance(1)
            elif self.mode.expects_element_name and (match := ELEMENT_NAME.match(self.source[self.curr :])):
                name = match.group()
                yield self.make_token(TokenType.ELEMENT_NAME, len(name))
                self.advance(len(name))
                self.mode.expects_element_name = False
            elif (
                not self.mode.expects_element_name
                and self.mode.is_inside_open_tag
                and (match := ATTRIBUTE_NAME.match(self.source[self.curr :]))
            ):
                attr = match.group()
                yield self.make_token(TokenType.ATTRIBUTE, len(attr))
                self.advance(len(attr))
            elif self.mode.is_inside_open_tag and (match := ATTRIBUTE_STRING_VALUE.match(self.source[self.curr :])):
                value = match.group()
                yield self.make_token(TokenType.ATTRIBUTE_VALUE, len(value))
                self.advance(len(value))
        elif match := JSX_TEXT.match(self.source[self.curr :]):
            text = match.group()
            yield self.make_token(TokenType.JSX_TEXT, len(text))
            self.advance(len(text))
        else:
            msg = f"Unexpected token {self.source[self.curr:]}"
            raise TokenizerError(msg)

    def tokenize_py(self) -> Generator[Token, None, None]:  # noqa: C901, PLR0912, PLR0915
        assert isinstance(self.mode, PYMode)
        if match := WS.match(self.source[self.curr :]):
            yield self.make_token(TokenType.WS, len(match.group()))
            self.advance(len(match.group()))
        elif match := COMMENT.match(self.source[self.curr :]):
            yield self.make_token(TokenType.COMMENT, len(match.group()))
            self.advance(len(match.group()))
            self.mode.prev_token = match.group()
        elif match := MULTI_LINE_STRING_START.match(self.source[self.curr :]):
            start = match.group(1)
            start_index = self.curr
            self.advance(len(match.group()))
            string = match.group()
            found = False
            while self.curr < len(self.source):
                if self.source[self.curr : self.curr + 2] == "\\\\":
                    string += "\\\\"
                    self.advance(2)
                elif self.source[self.curr : self.curr + 2] == "\\'":
                    string += "\\'"
                    self.advance(2)
                elif self.source[self.curr : self.curr + 2] == '\\"':
                    string += '\\"'
                    self.advance(2)
                elif self.source[self.curr : self.curr + 3] == start:
                    string += start
                    self.advance(3)
                    found = True
                    break
                else:
                    string += self.source[self.curr]
                    self.advance(1)

            if not found:
                msg = make_error_message(
                    "Unterminated string", self.source, start_index, start_index + len(match.group())
                )
                raise TokenizerError(msg)
            yield self.make_token(TokenType.MULTI_LINE_STRING, value=string, start=start_index, end=self.curr)
            self.mode.prev_token = string
        elif match := SINGLE_LINE_STRING_START.match(self.source[self.curr :]):
            start = match.group(1)
            start_index = self.curr
            self.advance(len(match.group()))
            string = match.group()
            found = False
            while self.curr < len(self.source):
                if self.source[self.curr : self.curr + 2] == "\\\\":
                    string += "\\\\"
                    self.advance(2)
                elif self.source[self.curr : self.curr + 2] == "\\'":
                    string += "\\'"
                    self.advance(2)
                elif self.source[self.curr : self.curr + 2] == '\\"':
                    string += '\\"'
                    self.advance(2)
                elif self.source[self.curr] == start:
                    string += start
                    self.advance(1)
                    found = True
                    break
                else:
                    string += self.source[self.curr]
                    self.advance(1)

            if not found:
                msg = make_error_message(
                    "Unterminated string", self.source, start_index, start_index + len(match.group())
                )
                raise TokenizerError(msg)
            yield self.make_token(TokenType.SINGLE_LINE_STRING, value=string, start=start_index, end=self.curr)
            self.mode.prev_token = string
        elif match := FSTRING_START.match(self.source[self.curr :]):
            start = match.group(1)
            start_index = self.curr
            string = match.group()
            yield self.make_token(TokenType.FSTRING_START, len(match.group()))
            self.advance(len(match.group()))
            self.mode.prev_token = string
            self.modes.append(FStringMode(start=start))
        elif self.source[self.curr] in {":", "(", "[", ",", "=", ":=", "->"}:
            yield self.make_token(TokenType.OP, 1)
            self.mode.prev_token = self.source[self.curr]
            self.advance(1)
        elif self.source[self.curr : self.curr + 2] in {":=", "->"}:
            op = self.source[self.curr : self.curr + 2]
            yield self.make_token(TokenType.OP, 2)
            self.mode.prev_token = op
            self.advance(2)
        elif match := JSX_KEYWORDS.match(self.source[self.curr :]):
            yield self.make_token(TokenType.ANY, len(match.group()))
            self.advance(len(match.group()))
            self.mode.prev_token = match.group()
        elif self.source[self.curr] == "{":
            self.mode.curly_brackets += 1
            yield self.make_token(TokenType.OP, 1)
            self.mode.prev_token = self.source[self.curr]
            self.advance(1)
        elif self.source[self.curr] == "}":
            self.mode.curly_brackets -= 1
            if (self.mode.inside_jsx or self.mode.inside_fstring) and self.mode.curly_brackets == 0:
                self.modes.pop()
            else:
                yield self.make_token(TokenType.OP, 1)
                self.mode.prev_token = self.source[self.curr]
                self.advance(1)
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
                yield self.make_token(TokenType.OP, 1)
                self.mode.prev_token = self.source[self.curr]
                self.advance(1)
        elif match := NAME.match(self.source[self.curr :]):
            yield self.make_token(TokenType.NAME, len(match.group()))
            self.advance(len(match.group()))
            self.mode.prev_token = match.group()
        else:
            yield self.make_token(TokenType.ANY, 1)
            self.mode.prev_token = self.source[self.curr]
            self.advance(1)

    def tokenize_fstring(self) -> Generator[Token, None, None]:
        assert isinstance(self.mode, FStringMode)
        start = self.mode.start
        if self.source[self.curr] == "{":
            yield self.make_token(TokenType.OP, 1)
            self.advance(1)
            self.modes.append(PYMode(curly_brackets=1, inside_jsx=False, inside_fstring=True))
        elif self.source[self.curr] == "}":
            yield self.make_token(TokenType.OP, 1)
            self.advance(1)
        elif self.source[self.curr : self.curr + len(start)] == start:
            yield self.make_token(TokenType.FSTRING_END, len(start))
            self.advance(len(start))
            self.modes.pop()
        else:
            middle = ""
            start_index = self.curr
            while self.curr < len(self.source):
                if self.source[self.curr : self.curr + 2] == "{{":
                    middle += "{{"
                    self.advance(2)
                elif self.source[self.curr : self.curr + 2] == "}}":
                    middle += "}}"
                    self.advance(2)
                elif (
                    self.source[self.curr] not in {"{", "}"}
                    and self.source[self.curr : self.curr + len(start)] != start
                ):
                    middle += self.source[self.curr]
                    self.advance(1)
                else:
                    break
            if not middle:
                msg = f"Unexpected token {self.source[self.curr:]}"
                raise TokenizerError(msg)
            yield self.make_token(TokenType.FSTRING_MIDDLE, value=middle, start=start_index, end=self.curr)

# https://homepages.inf.ed.ac.uk/wadler/papers/prettier/prettier.pdf