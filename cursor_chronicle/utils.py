"""
Shared utilities and constants for Cursor Chronicle.
"""

import platform
import signal
from pathlib import Path

# Handle broken pipe gracefully
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def get_cursor_paths() -> tuple:
    """
    Get standard Cursor IDE paths.

    Returns:
        Tuple of (cursor_config_path, workspace_storage_path, global_storage_path)
    """
    if platform.system() == "Darwin":
        cursor_config_path = (
            Path.home() / "Library" / "Application Support" / "Cursor" / "User"
        )
    else:
        cursor_config_path = Path.home() / ".config" / "Cursor" / "User"
    workspace_storage_path = cursor_config_path / "workspaceStorage"
    global_storage_path = cursor_config_path / "globalStorage" / "state.vscdb"
    return cursor_config_path, workspace_storage_path, global_storage_path


# Tool type mapping for display
TOOL_TYPES = {
    1: "🔍 Codebase Search",
    3: "🔎 Grep Search",
    5: "📖 Read File",
    6: "📁 List Directory",
    7: "✏️ Edit File",
    8: "🔍 File Search",
    9: "🔍 Codebase Search",
    11: "🗑️ Delete File",
    12: "🔄 Reapply",
    15: "⚡ Terminal Command",
    16: "📋 Fetch Rules",
    18: "🌐 Web Search",
    19: "🔧 MCP Tool",
}
