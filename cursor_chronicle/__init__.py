"""
Cursor Chronicle - Extract and display Cursor IDE chat history.
"""

from .cli import main, parse_date
from .formatters import (
    format_attached_files,
    format_dialog,
    format_token_info,
    format_tool_call,
    infer_model_from_context,
)
from .messages import (
    extract_attached_files,
    extract_files_from_layout,
    get_dialog_messages,
)
from .statistics import format_statistics, get_dialog_statistics, show_statistics
from .utils import TOOL_TYPES, get_cursor_paths
from .viewer import CursorChatViewer

__all__ = [
    # Main class
    "CursorChatViewer",
    # CLI
    "main",
    "parse_date",
    # Messages
    "get_dialog_messages",
    "extract_attached_files",
    "extract_files_from_layout",
    # Formatters
    "format_attached_files",
    "format_tool_call",
    "format_token_info",
    "format_dialog",
    "infer_model_from_context",
    # Statistics
    "get_dialog_statistics",
    "format_statistics",
    "show_statistics",
    # Utils
    "get_cursor_paths",
    "TOOL_TYPES",
]

__version__ = "1.4.0"
