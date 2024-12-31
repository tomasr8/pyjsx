from __future__ import annotations

import enum
import json
import logging
import os
from dataclasses import dataclass

from lsprotocol.types import (
    INITIALIZE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    InitializeParams,
    MessageType,
    PositionEncodingKind,
    Range,
)
from pygls import server, workspace
from pygls.workspace.position_codec import PositionCodec
from typing_extensions import Self


logger = logging.getLogger(__name__)


MAX_WORKERS = 1
LSP_SERVER = server.LanguageServer(
    name="PyJSX",
    version="0.0.1",
    max_workers=MAX_WORKERS,
)


###
# Document
###


@enum.unique
class DocumentKind(enum.Enum):
    """The kind of document."""

    Text = enum.auto()
    """A Python file."""

    Notebook = enum.auto()
    """A Notebook Document."""

    Cell = enum.auto()
    """A cell in a Notebook Document."""


@dataclass(frozen=True)
class Document:
    """A document representing either a Python file, a Notebook cell, or a Notebook."""

    uri: str
    path: str
    source: str
    kind: DocumentKind
    version: int | None

    @classmethod
    def from_text_document(cls, text_document: workspace.TextDocument) -> Self:
        """Create a `Document` from the given Text Document."""
        return cls(
            uri=text_document.uri,
            path=text_document.path,
            kind=DocumentKind.Text,
            source=text_document.source,
            version=text_document.version,
        )

    @classmethod
    def from_cell_or_text_uri(cls, uri: str) -> Self:
        """Create a `Document` representing either a Python file or a Notebook cell from
        the given URI.

        The function will try to get the Notebook cell first, and if there's no cell
        with the given URI, it will fallback to the text document.
        """
        notebook_document = LSP_SERVER.workspace.get_notebook_document(cell_uri=uri)
        if notebook_document is not None:
            notebook_cell = next(
                (notebook_cell for notebook_cell in notebook_document.cells if notebook_cell.document == uri),
                None,
            )
            if notebook_cell is not None:
                return cls.from_notebook_cell(notebook_cell)

        # Fall back to the Text Document representing a Python file.
        text_document = LSP_SERVER.workspace.get_text_document(uri)
        return cls.from_text_document(text_document)

    @classmethod
    def from_uri(cls, uri: str) -> Self:
        """Create a `Document` representing either a Python file or a Notebook from
        the given URI.

        The URI can be a file URI, a notebook URI, or a cell URI. The function will
        try to get the notebook document first, and if there's no notebook document
        with the given URI, it will fallback to the text document.
        """
        # First, try to get the Notebook Document assuming the URI is a Cell URI.
        notebook_document = LSP_SERVER.workspace.get_notebook_document(cell_uri=uri)
        if notebook_document is None:
            # If that fails, try to get the Notebook Document assuming the URI is a
            # Notebook URI.
            notebook_document = LSP_SERVER.workspace.get_notebook_document(notebook_uri=uri)
        if notebook_document:
            return cls.from_notebook_document(notebook_document)

        # Fall back to the Text Document representing a Python file.
        text_document = LSP_SERVER.workspace.get_text_document(uri)
        return cls.from_text_document(text_document)

    def is_stdlib_file(self) -> bool:
        """Return True if the document belongs to standard library."""
        return utils.is_stdlib_file(self.path)


###
# Linting.
###


@LSP_SERVER.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(params: DidOpenTextDocumentParams) -> None:
    """LSP handler for textDocument/didOpen request."""
    document = Document.from_text_document(LSP_SERVER.workspace.get_text_document(params.text_document.uri))
    # diagnostics = await _lint_document_impl(document, settings)
    LSP_SERVER.publish_diagnostics(document.uri, [])


@LSP_SERVER.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(params: DidCloseTextDocumentParams) -> None:
    """LSP handler for textDocument/didClose request."""
    text_document = LSP_SERVER.workspace.get_text_document(params.text_document.uri)
    # Publishing empty diagnostics to clear the entries for this file.
    LSP_SERVER.publish_diagnostics(text_document.uri, [])


###
# Lifecycle.
###


@LSP_SERVER.feature(INITIALIZE)
def initialize(params: InitializeParams) -> None:
    """LSP handler for initialize request."""
    # Extract client capabilities.
    # CLIENT_CAPABILITIES[CODE_ACTION_RESOLVE] = _supports_code_action_resolve(params.capabilities)

    # Extract `settings` from the initialization options.
    workspace_settings: list[WorkspaceSettings] | WorkspaceSettings | None = (params.initialization_options or {}).get(
        "settings",
    )
    global_settings: UserSettings | None = (params.initialization_options or {}).get("globalSettings", {})

    log_to_output(f"Workspace settings: " f"{json.dumps(workspace_settings, indent=4, ensure_ascii=False)}")
    log_to_output(f"Global settings: " f"{json.dumps(global_settings, indent=4, ensure_ascii=False)}")

    # Preserve any "global" settings.
    if global_settings:
        GLOBAL_SETTINGS.update(global_settings)
    elif isinstance(workspace_settings, dict):
        # In Sublime Text, Neovim, and probably others, we're passed a single
        # `settings`, which we'll treat as defaults for any future files.
        GLOBAL_SETTINGS.update(workspace_settings)

    # Update workspace settings.
    settings: list[WorkspaceSettings]
    if isinstance(workspace_settings, dict):
        settings = [workspace_settings]
    elif isinstance(workspace_settings, list):
        # In VS Code, we're passed a list of `settings`, one for each workspace folder.
        settings = workspace_settings
    else:
        settings = []

    # _update_workspace_settings(settings)


async def _run_format_on_document(
    document: Document, settings: WorkspaceSettings, format_range: Range | None = None
) -> ExecutableResult | None:
    """Runs the Ruff `format` subcommand on the given document source."""
    if settings.get("ignoreStandardLibrary", True) and document.is_stdlib_file():
        log_warning(f"Skipping standard library file: {document.path}")
        return None

    version_requirement = (
        VERSION_REQUIREMENT_FORMATTER if format_range is None else VERSION_REQUIREMENT_RANGE_FORMATTING
    )
    executable = _find_ruff_binary(settings, version_requirement)
    argv: list[str] = [
        "format",
        "--force-exclude",
        "--quiet",
        "--stdin-filename",
        document.path,
    ]

    if format_range:
        codec = PositionCodec(PositionEncodingKind.Utf16)
        format_range = codec.range_from_client_units(document.source.splitlines(True), format_range)

        argv.extend(
            [
                "--range",
                f"{format_range.start.line + 1}:{format_range.start.character + 1}-{format_range.end.line + 1}:{format_range.end.character + 1}",  # noqa: E501
            ]
        )

    for arg in settings.get("format", {}).get("args", []):
        if arg in UNSUPPORTED_FORMAT_ARGS:
            log_to_output(f"Ignoring unsupported argument: {arg}")
        else:
            argv.append(arg)

    return ExecutableResult(
        executable,
        *await run_path(
            executable.path,
            argv,
            cwd=settings["cwd"],
            source=document.source,
        ),
    )


###
# Logging.
###


def log_to_output(message: str) -> None:
    LSP_SERVER.show_message_log(message, MessageType.Log)


def show_error(message: str) -> None:
    """Show a pop-up with an error. Only use for critical errors."""
    LSP_SERVER.show_message_log(message, MessageType.Error)
    LSP_SERVER.show_message(message, MessageType.Error)


def log_warning(message: str) -> None:
    LSP_SERVER.show_message_log(message, MessageType.Warning)
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["onWarning", "always"]:
        LSP_SERVER.show_message(message, MessageType.Warning)


def log_always(message: str) -> None:
    LSP_SERVER.show_message_log(message, MessageType.Info)
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["always"]:
        LSP_SERVER.show_message(message, MessageType.Info)


###
# Start up.
###


def start() -> None:
    LSP_SERVER.start_io()


if __name__ == "__main__":
    start()
