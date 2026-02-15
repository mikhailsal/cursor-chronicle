"""
Export dialogs to Markdown files.

Creates a folder structure: <project_name>/<YYYY-MM>/<date_time_title>.md
Dialogs are placed by their creation date, not last updated date.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .config import (
    VERBOSITY_COMPACT,
    VERBOSITY_FULL,
    VERBOSITY_STANDARD,
    get_export_path,
    get_verbosity,
    load_config,
)
from .messages import get_dialog_messages
from .utils import TOOL_TYPES
from .viewer import CursorChatViewer


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """
    Sanitize a dialog name for use as a filename.

    Replaces spaces and special characters with underscores.
    Truncates to max_length characters.

    Args:
        name: The dialog name to sanitize.
        max_length: Maximum length of the resulting filename part.

    Returns:
        A safe filename string.
    """
    if not name or not name.strip():
        return "Untitled"

    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    sanitized = re.sub(r'\s+', '_', sanitized)
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = sanitized.strip('_. ')

    if not sanitized:
        return "Untitled"

    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip('_')

    return sanitized


def sanitize_project_name(name: str) -> str:
    """
    Sanitize a project name for use as a directory name.

    Args:
        name: The project name to sanitize.

    Returns:
        A safe directory name string.
    """
    if not name or not name.strip():
        return "Unknown_Project"

    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    sanitized = re.sub(r'\s+', '_', sanitized)
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = sanitized.strip('_. ')

    return sanitized if sanitized else "Unknown_Project"


def build_md_filename(created_at: int, dialog_name: str) -> str:
    """
    Build a Markdown filename from creation timestamp and dialog name.

    Format: YYYY-MM-DD_HH-MM_Sanitized_Title.md

    Args:
        created_at: Creation timestamp in milliseconds.
        dialog_name: The dialog name/title.

    Returns:
        Filename string like "2025-06-12_14-31_How_we_should_implement_logging.md"
    """
    if created_at:
        dt = datetime.fromtimestamp(created_at / 1000)
        date_prefix = dt.strftime("%Y-%m-%d_%H-%M")
    else:
        date_prefix = "0000-00-00_00-00"

    safe_name = sanitize_filename(dialog_name)
    return f"{date_prefix}_{safe_name}.md"


def build_folder_path(project_name: str, created_at: int) -> str:
    """
    Build the folder path for a dialog based on project and creation date.

    Format: <project_name>/<YYYY-MM>/

    Args:
        project_name: The project name.
        created_at: Creation timestamp in milliseconds.

    Returns:
        Relative folder path like "myProject/2025-06"
    """
    safe_project = sanitize_project_name(project_name)

    if created_at:
        dt = datetime.fromtimestamp(created_at / 1000)
        year_month = dt.strftime("%Y-%m")
    else:
        year_month = "0000-00"

    return os.path.join(safe_project, year_month)


def format_message_md(message: Dict, verbosity: int) -> str:
    """
    Format a single message as Markdown.

    Args:
        message: Message dict from get_dialog_messages.
        verbosity: Verbosity level (1=compact, 2=standard, 3=full).

    Returns:
        Markdown-formatted string for the message.
    """
    message_type = message.get("type")
    text = message.get("text", "").strip()
    tool_data = message.get("tool_data")
    attached_files = message.get("attached_files", [])
    is_thought = message.get("is_thought", False)
    thinking_duration = message.get("thinking_duration", 0)
    thinking_content = message.get("thinking_content", "")

    if not text and not tool_data and not attached_files and not is_thought:
        return ""

    lines = []

    if is_thought:
        if verbosity >= VERBOSITY_STANDARD:
            lines.append("### 🧠 AI Thinking")
            if thinking_duration > 0:
                lines.append(f"*Duration: {thinking_duration / 1000:.1f}s*")
            lines.append("")
            if thinking_content and verbosity == VERBOSITY_FULL:
                lines.append(thinking_content)
            elif thinking_content:
                truncated = thinking_content[:500]
                if len(thinking_content) > 500:
                    truncated += "..."
                lines.append(truncated)
            lines.append("")
        return "\n".join(lines)

    if message_type == 1:
        lines.append("### 👤 User")
        lines.append("")
        if text:
            lines.append(text)
            lines.append("")
        if attached_files and verbosity >= VERBOSITY_STANDARD:
            lines.append(_format_attached_files_md(attached_files, verbosity))
            lines.append("")

    elif message_type == 2:
        if tool_data:
            tool_output = _format_tool_call_md(tool_data, verbosity)
            if tool_output:
                lines.append(tool_output)
                lines.append("")
        if text:
            lines.append("### 🤖 Assistant")
            lines.append("")
            lines.append(text)
            lines.append("")
            if verbosity >= VERBOSITY_STANDARD:
                token_info = _format_token_info_md(message)
                if token_info:
                    lines.append(token_info)
                    lines.append("")
    else:
        if text or tool_data:
            lines.append(f"### 📝 Message (type {message_type})")
            lines.append("")
            if text:
                lines.append(text)
                lines.append("")
            if tool_data:
                tool_output = _format_tool_call_md(tool_data, verbosity)
                if tool_output:
                    lines.append(tool_output)
                    lines.append("")

    return "\n".join(lines)


def _format_attached_files_md(attached_files: List[Dict], verbosity: int) -> str:
    """Format attached files as Markdown."""
    if not attached_files:
        return ""

    lines = ["**Attached Files:**", ""]

    for file_info in attached_files:
        file_type = file_info.get("type", "unknown")
        file_path = file_info.get("path", "unknown")

        type_icons = {
            "active": "📍",
            "selected": "✅",
            "context": "📎",
            "relevant": "🔗",
            "project": "📁",
            "selected_context": "🎯",
        }
        icon = type_icons.get(file_type, "📄")
        lines.append(f"- {icon} `{file_path}` ({file_type})")

        if verbosity == VERBOSITY_FULL:
            if file_info.get("content"):
                content = file_info["content"]
                lines.append(f"  ```")
                lines.append(f"  {content}")
                lines.append(f"  ```")

    return "\n".join(lines)


def _format_tool_call_md(tool_data: Dict, verbosity: int) -> str:
    """Format a tool call as Markdown."""
    if not tool_data or (tool_data.get("tool") is None and not tool_data.get("name")):
        return ""

    tool_type = tool_data.get("tool")
    tool_name = tool_data.get("name", "unknown")
    status = tool_data.get("status", "unknown")

    tool_icon = "🔧 Unknown Tool"
    if isinstance(tool_type, int) and tool_type in TOOL_TYPES:
        tool_icon = TOOL_TYPES[tool_type]

    lines = []

    if verbosity == VERBOSITY_COMPACT:
        lines.append(f"> 🛠️ **Tool:** {tool_icon} — `{tool_name}` ({status})")
        return "\n".join(lines)

    lines.append(f"#### 🛠️ Tool: {tool_icon}")
    lines.append(f"- **Name:** `{tool_name}`")
    lines.append(f"- **Status:** {status}")

    user_decision = tool_data.get("userDecision", "unknown")
    if user_decision != "unknown":
        decision_icon = "✅" if user_decision == "accepted" else "❌"
        lines.append(f"- **Decision:** {decision_icon} {user_decision}")

    if verbosity >= VERBOSITY_STANDARD:
        import json

        raw_args = tool_data.get("rawArgs")
        if raw_args:
            try:
                if isinstance(raw_args, dict):
                    args = raw_args
                elif isinstance(raw_args, str):
                    args = json.loads(raw_args)
                else:
                    args = None
                if args and isinstance(args, dict):
                    lines.append("")
                    lines.append("**Parameters:**")
                    for key, value in args.items():
                        if isinstance(value, str) and len(value) > 200 and verbosity < VERBOSITY_FULL:
                            value = value[:200] + "..."
                        lines.append(f"- `{key}`: {value}")
            except (json.JSONDecodeError, TypeError):
                pass

        if verbosity == VERBOSITY_FULL:
            result = tool_data.get("result")
            if result:
                try:
                    if isinstance(result, (dict, list)):
                        result_data = result
                    elif isinstance(result, str):
                        result_data = json.loads(result)
                    else:
                        result_data = None
                    if result_data is not None:
                        result_str = json.dumps(result_data, indent=2, ensure_ascii=False)
                        lines.append("")
                        lines.append("**Result:**")
                        lines.append("```")
                        lines.append(result_str)
                        lines.append("```")
                except (json.JSONDecodeError, TypeError):
                    pass

    return "\n".join(lines)


def _format_token_info_md(message: Dict) -> str:
    """Format token usage as Markdown."""
    token_count = message.get("token_count", {})
    if not token_count:
        return ""

    input_tokens = token_count.get("inputTokens", 0)
    output_tokens = token_count.get("outputTokens", 0)
    total = input_tokens + output_tokens

    if total == 0:
        return ""

    return f"*Tokens: {input_tokens} → {output_tokens} ({total} total)*"


def format_dialog_md(
    messages: List[Dict],
    dialog_name: str,
    project_name: str,
    created_at: int,
    last_updated: int,
    verbosity: int,
) -> str:
    """
    Format an entire dialog as a Markdown document.

    Args:
        messages: List of message dicts.
        dialog_name: Dialog title.
        project_name: Project name.
        created_at: Creation timestamp in ms.
        last_updated: Last updated timestamp in ms.
        verbosity: Verbosity level.

    Returns:
        Complete Markdown document as string.
    """
    lines = []

    # Header
    lines.append(f"# {dialog_name}")
    lines.append("")
    lines.append(f"**Project:** {project_name}")

    if created_at:
        dt = datetime.fromtimestamp(created_at / 1000)
        lines.append(f"**Created:** {dt.strftime('%Y-%m-%d %H:%M')}")
    if last_updated:
        dt = datetime.fromtimestamp(last_updated / 1000)
        lines.append(f"**Last Updated:** {dt.strftime('%Y-%m-%d %H:%M')}")

    lines.append(f"**Messages:** {len(messages)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Messages
    for message in messages:
        md = format_message_md(message, verbosity)
        if md:
            lines.append(md)
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def export_dialogs(
    viewer: CursorChatViewer,
    export_path: Optional[Path] = None,
    verbosity: Optional[int] = None,
    project_filter: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    progress_callback: Optional[Callable[[Dict], None]] = None,
) -> Dict:
    """
    Export all dialogs to Markdown files.

    Creates folder structure: <export_path>/<project>/<YYYY-MM>/<file>.md

    Args:
        viewer: CursorChatViewer instance.
        export_path: Override export path (uses config if None).
        verbosity: Override verbosity level (uses config if None).
        project_filter: Filter by project name (partial match).
        start_date: Filter dialogs created after this date.
        end_date: Filter dialogs created before this date.
        progress_callback: Optional callback called after each dialog.
            Receives dict with keys: current, total, project_name,
            dialog_name, status ('exported'|'skipped'|'error'), percent.

    Returns:
        Dict with export statistics.
    """
    config = load_config()

    if export_path is None:
        export_path = get_export_path(config)
    if verbosity is None:
        verbosity = get_verbosity(config)

    # Get all dialogs sorted by creation date
    dialogs = viewer.get_all_dialogs(
        start_date=start_date,
        end_date=end_date,
        project_filter=project_filter,
        sort_by="date",
        sort_desc=False,
        use_updated=False,
    )

    stats = {
        "total_dialogs": len(dialogs),
        "exported": 0,
        "errors": 0,
        "skipped": 0,
        "export_path": str(export_path),
        "verbosity": verbosity,
    }

    if not dialogs:
        return stats

    total = len(dialogs)
    for idx, dialog in enumerate(dialogs, 1):
        composer_id = dialog.get("composer_id")
        dialog_name = dialog.get("name", "Untitled")
        project_name = dialog.get("project_name", "Unknown")
        created_at = dialog.get("created_at", 0)
        last_updated = dialog.get("last_updated", 0)
        status = "exported"

        try:
            messages = get_dialog_messages(composer_id)
        except Exception:
            stats["errors"] += 1
            status = "error"
            _notify_progress(progress_callback, idx, total, project_name, dialog_name, status)
            continue

        if not messages:
            stats["skipped"] += 1
            status = "skipped"
            _notify_progress(progress_callback, idx, total, project_name, dialog_name, status)
            continue

        # Build paths
        folder_rel = build_folder_path(project_name, created_at)
        filename = build_md_filename(created_at, dialog_name)
        folder_abs = export_path / folder_rel
        file_path = folder_abs / filename

        # Create directory
        folder_abs.mkdir(parents=True, exist_ok=True)

        # Format and write
        md_content = format_dialog_md(
            messages=messages,
            dialog_name=dialog_name,
            project_name=project_name,
            created_at=created_at,
            last_updated=last_updated,
            verbosity=verbosity,
        )

        try:
            # Replace surrogate characters that can't be encoded in UTF-8
            md_content = md_content.encode("utf-8", errors="surrogatepass").decode(
                "utf-8", errors="replace"
            )
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            stats["exported"] += 1
        except OSError:
            stats["errors"] += 1
            status = "error"

        _notify_progress(progress_callback, idx, total, project_name, dialog_name, status)

    return stats


def _notify_progress(
    callback: Optional[Callable[[Dict], None]],
    current: int,
    total: int,
    project_name: str,
    dialog_name: str,
    status: str,
) -> None:
    """Call progress callback if provided."""
    if callback is None:
        return
    percent = int(current * 100 / total) if total > 0 else 0
    callback({
        "current": current,
        "total": total,
        "project_name": project_name,
        "dialog_name": dialog_name,
        "status": status,
        "percent": percent,
    })


def show_export_summary(stats: Dict) -> str:
    """
    Format export statistics for display.

    Args:
        stats: Dict from export_dialogs.

    Returns:
        Formatted summary string.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("📤 CURSOR CHRONICLE - EXPORT SUMMARY")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Export path:    {stats['export_path']}")
    lines.append(f"  Verbosity:     {stats['verbosity']} "
                 f"({'compact' if stats['verbosity'] == 1 else 'standard' if stats['verbosity'] == 2 else 'full'})")
    lines.append("")
    lines.append(f"  Total dialogs: {stats['total_dialogs']}")
    lines.append(f"  ✅ Exported:    {stats['exported']}")
    if stats['skipped']:
        lines.append(f"  ⏭️  Skipped:     {stats['skipped']} (empty)")
    if stats['errors']:
        lines.append(f"  ❌ Errors:      {stats['errors']}")
    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
