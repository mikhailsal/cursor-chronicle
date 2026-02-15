"""
Markdown formatting functions for dialog export.

This module contains all the formatting logic for converting dialog messages
to Markdown format. It's used by the exporter module.
"""

import json
from datetime import datetime
from typing import Dict, List

from .config import VERBOSITY_COMPACT, VERBOSITY_FULL, VERBOSITY_STANDARD
from .utils import TOOL_TYPES


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
                lines.append("  ```")
                lines.append(f"  {content}")
                lines.append("  ```")

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
