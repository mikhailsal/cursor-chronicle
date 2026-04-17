"""
Shared utilities and constants for Cursor Chronicle.
"""

import os
import signal
import sys
from pathlib import Path

# Handle broken pipe gracefully
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# Absolute path to Cursor's per-user "User" directory (contains workspaceStorage, etc.).
# When set (non-empty after stripping), overrides OS-specific defaults below.
CURSOR_USER_DIR_ENV = "CURSOR_CHRONICLE_CURSOR_USER_DIR"


def _cursor_user_dir() -> Path:
    """
    Directory where Cursor stores per-user data (workspaceStorage, globalStorage, etc.).

    Override with the environment variable CURSOR_CHRONICLE_CURSOR_USER_DIR (tilde expands).

    Otherwise matches VS Code-style layout: macOS and Windows use app support / roaming;
    Linux and other Unixes use XDG-style ~/.config.
    """
    override = os.environ.get(CURSOR_USER_DIR_ENV)
    if override is not None and override.strip():
        return Path(override.strip()).expanduser()

    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Cursor" / "User"
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Cursor" / "User"
        return home / "AppData" / "Roaming" / "Cursor" / "User"
    return home / ".config" / "Cursor" / "User"


def get_cursor_paths() -> tuple:
    """
    Get standard Cursor IDE paths for the current OS.

    If CURSOR_CHRONICLE_CURSOR_USER_DIR is set, it is used as the Cursor User directory.

    Returns:
        Tuple of (cursor_config_path, workspace_storage_path, global_storage_path)
    """
    cursor_config_path = _cursor_user_dir()
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
