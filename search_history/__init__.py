"""
Cursor Chronicle Search - Search through Cursor IDE chat history.
"""

from .cli import main
from .formatters import format_full_dialog, format_search_results, highlight_query
from .searcher import CursorHistorySearch

__all__ = [
    "CursorHistorySearch",
    "main",
    "format_search_results",
    "format_full_dialog",
    "highlight_query",
]

__version__ = "1.4.0"
