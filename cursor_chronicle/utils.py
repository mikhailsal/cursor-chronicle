"""
Shared utilities and constants for Cursor Chronicle.
"""

import os
import platform
import signal
from pathlib import Path

# Handle broken pipe gracefully
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def resolve_cursor_user_dir() -> Path:
    """
    Resolve Cursor's "User" directory with ENV override and OS detection.

    Priority:
    1. CURSOR_USER_DIR
    2. Platform defaults
    """
    env_override = os.getenv("CURSOR_USER_DIR")
    if env_override:
        return Path(env_override).expanduser()

    system_name = platform.system().lower()
    home = Path.home()

    if system_name == "darwin":
        return home / "Library" / "Application Support" / "Cursor" / "User"

    if system_name == "windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "Cursor" / "User"
        return home / "AppData" / "Roaming" / "Cursor" / "User"

    return home / ".config" / "Cursor" / "User"


def get_cursor_paths() -> tuple:
    """
    Get standard Cursor IDE paths.
    
    Returns:
        Tuple of (cursor_config_path, workspace_storage_path, global_storage_path)
    """
    cursor_config_path = resolve_cursor_user_dir()
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
