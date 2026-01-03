"""
Message extraction and processing from Cursor database.
"""

import base64
import json
import sqlite3
from typing import Dict, List

from pathlib import Path
from typing import Optional

from .utils import get_cursor_paths

# Module-level override for testing
_global_storage_override: Optional[Path] = None


def get_dialog_messages(composer_id: str, db_path: Optional[Path] = None) -> List[Dict]:
    """Get all dialog messages by composer ID."""
    if db_path:
        global_storage_path = db_path
    elif _global_storage_override:
        global_storage_path = _global_storage_override
    else:
        _, _, global_storage_path = get_cursor_paths()

    if not global_storage_path.exists():
        raise FileNotFoundError(f"Global database not found: {global_storage_path}")

    conn = sqlite3.connect(global_storage_path)
    cursor = conn.cursor()

    cursor.execute(
        """SELECT value FROM cursorDiskKV 
        WHERE key = ? AND LENGTH(value) > 100""",
        (f"composerData:{composer_id}",),
    )

    composer_result = cursor.fetchone()
    ordered_bubble_ids = []

    if composer_result:
        try:
            composer_data = json.loads(composer_result[0])
            if "fullConversationHeadersOnly" in composer_data:
                ordered_bubble_ids = [
                    bubble["bubbleId"]
                    for bubble in composer_data["fullConversationHeadersOnly"]
                ]
        except json.JSONDecodeError:
            pass

    if not ordered_bubble_ids:
        cursor.execute(
            """SELECT rowid, key, value FROM cursorDiskKV 
            WHERE key LIKE ? AND LENGTH(value) > 100 
            ORDER BY rowid""",
            (f"bubbleId:{composer_id}:%",),
        )
        results = cursor.fetchall()
    else:
        results = []
        for bubble_id in ordered_bubble_ids:
            cursor.execute(
                """SELECT rowid, key, value FROM cursorDiskKV 
                WHERE key = ? AND LENGTH(value) > 100""",
                (f"bubbleId:{composer_id}:{bubble_id}",),
            )
            result = cursor.fetchone()
            if result:
                results.append(result)

    conn.close()

    messages = []
    for rowid, key, value in results:
        try:
            bubble_data = json.loads(value)
            text = bubble_data.get("text", "").strip()
            bubble_type = bubble_data.get("type")
            tool_data = bubble_data.get("toolFormerData")
            thinking_data = bubble_data.get("thinking")

            message = {
                "text": text,
                "type": bubble_type,
                "bubble_id": bubble_data.get("bubbleId", ""),
                "key": key,
                "rowid": rowid,
                "tool_data": tool_data,
                "attached_files": extract_attached_files(bubble_data),
                "is_thought": False,
                "thinking_duration": 0,
                "thinking_content": "",
                "token_count": bubble_data.get("tokenCount", {}),
                "usage_uuid": bubble_data.get("usageUuid"),
                "server_bubble_id": bubble_data.get("serverBubbleId"),
                "is_agentic": bubble_data.get("isAgentic", False),
                "capabilities_ran": bubble_data.get("capabilitiesRan", {}),
                "unified_mode": bubble_data.get("unifiedMode"),
                "use_web": bubble_data.get("useWeb", False),
                "is_refunded": bubble_data.get("isRefunded", False),
            }

            if bubble_type == 2 and not text:
                is_thought_bubble = (
                    bubble_data.get("isThought")
                    or bubble_data.get("thinking")
                    or bubble_data.get("thinkingDurationMs")
                    or thinking_data
                )
                if is_thought_bubble:
                    message["is_thought"] = True
                    message["thinking_duration"] = bubble_data.get("thinkingDurationMs", 0)
                    thinking_content = _extract_thinking_content(thinking_data)
                    message["thinking_content"] = thinking_content

            messages.append(message)

        except json.JSONDecodeError:
            continue

    return messages


def _extract_thinking_content(thinking_data) -> str:
    """Extract thinking content from various possible fields."""
    if not thinking_data:
        return ""

    if isinstance(thinking_data, dict):
        thinking_content = (
            thinking_data.get("content")
            or thinking_data.get("text")
            or thinking_data.get("thinking")
            or thinking_data.get("signature")
            or ""
        )
        if thinking_content and thinking_content.startswith("AVSoXO"):
            try:
                decoded = base64.b64decode(thinking_content).decode("utf-8")
                thinking_content = decoded
            except Exception:
                pass
        return thinking_content
    elif isinstance(thinking_data, str):
        return thinking_data

    return ""


def extract_attached_files(bubble_data: Dict) -> List[Dict]:
    """Extract information about attached files from bubble data."""
    attached_files = []

    # 1. Active file (open in editor)
    current_file_data = bubble_data.get("currentFileLocationData")
    if current_file_data:
        file_path = (
            current_file_data.get("uri")
            or current_file_data.get("path")
            or current_file_data.get("filePath")
            or current_file_data.get("file")
        )
        if file_path:
            attached_files.append({
                "type": "active",
                "path": file_path,
                "line": current_file_data.get("line"),
                "preview": current_file_data.get("preview"),
            })

    # 2. Project layouts
    project_layouts = bubble_data.get("projectLayouts", [])
    for layout in project_layouts:
        if isinstance(layout, str):
            try:
                layout_data = json.loads(layout)
                if isinstance(layout_data, dict):
                    files = extract_files_from_layout(layout_data)
                    for file_path in files:
                        attached_files.append({"type": "project", "path": file_path})
            except json.JSONDecodeError:
                continue
        elif isinstance(layout, dict):
            files = extract_files_from_layout(layout)
            for file_path in files:
                attached_files.append({"type": "project", "path": file_path})

    # 3. Context chunks
    context_chunks = bubble_data.get("codebaseContextChunks", [])
    for chunk in context_chunks:
        if isinstance(chunk, dict):
            file_path = chunk.get("relativeWorkspacePath")
            if file_path:
                attached_files.append({
                    "type": "context",
                    "path": file_path,
                    "content": chunk.get("contents", ""),
                    "line_range": chunk.get("lineRange"),
                })

    # 4. Relevant files
    relevant_files = bubble_data.get("relevantFiles", [])
    for file_info in relevant_files:
        if isinstance(file_info, dict):
            file_path = file_info.get("path") or file_info.get("uri")
            if file_path:
                attached_files.append({"type": "relevant", "path": file_path})
        elif isinstance(file_info, str):
            attached_files.append({"type": "relevant", "path": file_info})

    # 5. Attached code chunks
    attached_chunks = bubble_data.get("attachedCodeChunks", [])
    for chunk in attached_chunks:
        if isinstance(chunk, dict):
            file_path = chunk.get("path") or chunk.get("uri")
            if file_path:
                attached_files.append({
                    "type": "selected",
                    "path": file_path,
                    "content": chunk.get("content", ""),
                    "selection": chunk.get("selection"),
                })

    # 6. File selections from context
    context = bubble_data.get("context", {})
    if isinstance(context, dict):
        file_selections = context.get("fileSelections", [])
        for selection in file_selections:
            if isinstance(selection, dict):
                file_path = selection.get("path") or selection.get("uri")
                if file_path:
                    attached_files.append({
                        "type": "selected_context",
                        "path": file_path,
                        "selection": selection.get("selection"),
                    })

    return attached_files


def extract_files_from_layout(layout_data: Dict, current_path: str = "") -> List[str]:
    """Recursively extract all file paths from project structure."""
    files = []

    if isinstance(layout_data, dict):
        for key, value in layout_data.items():
            new_path = f"{current_path}/{key}" if current_path else key

            if isinstance(value, dict):
                files.extend(extract_files_from_layout(value, new_path))
            elif value is None:
                files.append(new_path)

    return files
