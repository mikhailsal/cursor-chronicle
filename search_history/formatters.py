"""
Output formatting for search results.
"""

import re
from datetime import datetime
from typing import Dict, List


def highlight_query(text: str, query: str) -> str:
    """Highlight query in text using ANSI colors."""
    pattern = re.compile(f"({re.escape(query)})", re.IGNORECASE)
    return pattern.sub(r"\033[1;33m\1\033[0m", text)


def format_search_results(
    results: List[Dict],
    query: str,
    searcher,
    show_context: bool = False,
    context_size: int = 3,
) -> str:
    """Format search results for display."""
    if not results:
        return f"No results found for '{query}'"

    output = []
    output.append(f"🔍 Search results for '{query}'")
    output.append(f"   Found {len(results)} match(es)")
    output.append("=" * 60)

    dialogs = {}
    for result in results:
        dialog_key = (result["composer_id"], result["dialog_name"])
        if dialog_key not in dialogs:
            dialogs[dialog_key] = {
                "project_name": result["project_name"],
                "folder_path": result["folder_path"],
                "dialog_name": result["dialog_name"],
                "composer_id": result["composer_id"],
                "last_updated": result["last_updated"],
                "created_at": result["created_at"],
                "matches": [],
            }
        dialogs[dialog_key]["matches"].append(result)

    for dialog_key, dialog_info in dialogs.items():
        output.append("")
        output.append(f"📁 Project: {dialog_info['project_name']}")
        output.append(f"💬 Dialog: {dialog_info['dialog_name']}")

        if dialog_info["last_updated"]:
            date = datetime.fromtimestamp(dialog_info["last_updated"] / 1000)
            output.append(f"📅 Last updated: {date.strftime('%Y-%m-%d %H:%M')}")
        if dialog_info["created_at"]:
            date = datetime.fromtimestamp(dialog_info["created_at"] / 1000)
            output.append(f"📅 Created: {date.strftime('%Y-%m-%d %H:%M')}")

        output.append(f"🔗 Composer ID: {dialog_info['composer_id']}")
        output.append("-" * 40)

        for match in dialog_info["matches"]:
            field = match.get("field", "unknown")
            content = match.get("content", "")
            msg_type = match.get("type")

            type_icon = "📝"
            if msg_type == 1:
                type_icon = "👤 USER"
            elif msg_type == 2:
                type_icon = "🤖 AI"

            if field in ("tool_args", "tool_result"):
                type_icon = f"🛠️ Tool: {match.get('tool_name', 'unknown')}"

            output.append(f"   {type_icon}")

            highlighted = highlight_query(content, query)
            if len(highlighted) > 500:
                lower_content = content.lower()
                lower_query = query.lower()
                pos = lower_content.find(lower_query)
                if pos != -1:
                    start = max(0, pos - 200)
                    end = min(len(content), pos + len(query) + 200)
                    highlighted = "..." + highlight_query(content[start:end], query) + "..."
                else:
                    highlighted = highlighted[:500] + "..."

            output.append(f"   {highlighted}")
            output.append("")

        if show_context:
            output.append("   📜 CONTEXT:")
            for match in dialog_info["matches"][:1]:
                context = searcher.get_dialog_context(
                    match["composer_id"],
                    match["bubble_id"],
                    context_size,
                )
                for msg in context:
                    icon = "👤" if msg["type"] == 1 else "🤖"
                    if msg["is_target"]:
                        icon = "➡️" + icon
                    text = msg["text"][:200] + "..." if len(msg["text"]) > 200 else msg["text"]
                    output.append(f"      {icon}: {text}")
            output.append("")

    return "\n".join(output)


def format_full_dialog(
    messages: List[Dict], dialog_name: str, project_name: str
) -> str:
    """Format full dialog for display."""
    output = []
    output.append("=" * 60)
    output.append(f"PROJECT: {project_name}")
    output.append(f"DIALOG: {dialog_name}")
    output.append("=" * 60)
    output.append("")

    for message in messages:
        msg_type = message.get("type")
        text = message.get("text", "")
        tool_data = message.get("tool_data")

        if msg_type == 1:
            output.append("👤 USER:")
            if text:
                output.append(text)
            output.append("-" * 40)
        elif msg_type == 2:
            if tool_data:
                tool_name = tool_data.get("name", "unknown")
                status = tool_data.get("status", "unknown")
                output.append(f"🛠️ TOOL: {tool_name} ({status})")
                output.append("-" * 40)

            if text:
                output.append("🤖 AI:")
                output.append(text)
                output.append("-" * 40)
        else:
            if text:
                output.append(f"📝 MESSAGE (type {msg_type}):")
                output.append(text)
                output.append("-" * 40)

    return "\n".join(output)
