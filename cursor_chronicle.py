#!/usr/bin/env python3
"""
Cursor Chronicle
Extracts and displays dialogs from Cursor IDE database with support for
attached files.
"""

import argparse
import base64
import json
import os
import signal
import sqlite3
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Handle broken pipe gracefully
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


class CursorChatViewer:
    def __init__(self):
        self.cursor_config_path = Path.home() / ".config" / "Cursor" / "User"
        self.workspace_storage_path = self.cursor_config_path / "workspaceStorage"
        self.global_storage_path = (
            self.cursor_config_path / "globalStorage" / "state.vscdb"
        )

        # Tool type mapping
        self.tool_types = {
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

    def get_projects(self) -> List[Dict]:
        """Get list of all projects with their metadata"""
        projects = []

        if not self.workspace_storage_path.exists():
            return projects

        for workspace_dir in self.workspace_storage_path.iterdir():
            if not workspace_dir.is_dir():
                continue

            workspace_json = workspace_dir / "workspace.json"
            state_db = workspace_dir / "state.vscdb"

            if not workspace_json.exists() or not state_db.exists():
                continue

            try:
                # Read project information
                with open(workspace_json, "r") as f:
                    workspace_data = json.load(f)

                folder_uri = workspace_data.get("folder", "")
                if folder_uri.startswith("file://"):
                    folder_path = urllib.parse.unquote(folder_uri[7:])
                    project_name = os.path.basename(folder_path)
                else:
                    project_name = folder_uri

                # Read composer data from database
                conn = sqlite3.connect(state_db)
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT value FROM ItemTable WHERE key = " "'composer.composerData'"
                )
                result = cursor.fetchone()

                if result:
                    composer_data = json.loads(result[0])
                    composers = composer_data.get("allComposers", [])

                    # Find the most recent dialog
                    latest_dialog = None
                    if composers:
                        latest_dialog = max(
                            composers, key=lambda x: x.get("lastUpdatedAt", 0)
                        )

                    projects.append(
                        {
                            "workspace_id": workspace_dir.name,
                            "project_name": project_name,
                            "folder_path": (
                                folder_path
                                if folder_uri.startswith("file://")
                                else folder_uri
                            ),
                            "composers": composers,
                            "latest_dialog": latest_dialog,
                            "state_db_path": str(state_db),
                        }
                    )

                conn.close()

            except Exception:
                print(f"Error processing project {workspace_dir.name}")
                continue

        # Sort projects by last dialog time
        projects.sort(
            key=lambda x: (
                x["latest_dialog"].get("lastUpdatedAt", 0) if x["latest_dialog"] else 0
            ),
            reverse=True,
        )
        return projects

    def get_dialog_messages(self, composer_id: str) -> List[Dict]:
        """Get all dialog messages by composer ID"""
        if not self.global_storage_path.exists():
            raise FileNotFoundError(
                f"Global database not found: " f"{self.global_storage_path}"
            )

        conn = sqlite3.connect(self.global_storage_path)
        cursor = conn.cursor()

        # First get composer data for correct order
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
                # Get correct order from fullConversationHeadersOnly
                if "fullConversationHeadersOnly" in composer_data:
                    ordered_bubble_ids = [
                        bubble["bubbleId"]
                        for bubble in composer_data["fullConversationHeadersOnly"]
                    ]
            except json.JSONDecodeError:
                pass

        # If no fullConversationHeadersOnly, use old method
        if not ordered_bubble_ids:
            cursor.execute(
                """SELECT rowid, key, value FROM cursorDiskKV 
                WHERE key LIKE ? AND LENGTH(value) > 100 
                ORDER BY rowid""",
                (f"bubbleId:{composer_id}:%",),
            )
            results = cursor.fetchall()
        else:
            # Get bubbles in correct order
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
                    "attached_files": self.extract_attached_files(bubble_data),
                    "is_thought": False,  # Default to False
                    "thinking_duration": 0,  # Default to 0
                    "thinking_content": "",  # Default to empty
                    "token_count": bubble_data.get("tokenCount", {}),
                    "usage_uuid": bubble_data.get("usageUuid"),
                    "server_bubble_id": bubble_data.get("serverBubbleId"),
                    "is_agentic": bubble_data.get("isAgentic", False),
                    "capabilities_ran": bubble_data.get("capabilitiesRan", {}),
                    "unified_mode": bubble_data.get("unifiedMode"),
                    "use_web": bubble_data.get("useWeb", False),
                    "is_refunded": bubble_data.get("isRefunded", False),
                }

                # Check for AI thinking bubbles - improved logic
                if bubble_type == 2 and not text:
                    # Check multiple possible fields for thinking indication
                    is_thought_bubble = (
                        bubble_data.get("isThought")
                        or bubble_data.get("thinking")
                        or bubble_data.get("thinkingDurationMs")
                        or thinking_data
                    )
                    if is_thought_bubble:
                        message["is_thought"] = True
                        message["thinking_duration"] = bubble_data.get(
                            "thinkingDurationMs", 0
                        )

                        # Extract thinking content from various possible fields
                        thinking_content = ""
                        if thinking_data:
                            if isinstance(thinking_data, dict):
                                # Try different fields that might contain
                                # thinking content
                                thinking_content = (
                                    thinking_data.get("content")
                                    or thinking_data.get("text")
                                    or thinking_data.get("thinking")
                                    or thinking_data.get("signature")
                                    or ""
                                )
                                # If signature contains encoded content,
                                # try to decode it
                                if thinking_content and thinking_content.startswith(
                                    "AVSoXO"
                                ):
                                    # This appears to be base64 encoded
                                    # thinking content
                                    try:
                                        # Try to decode the signature
                                        # (it might be base64)
                                        decoded = base64.b64decode(
                                            thinking_content
                                        ).decode("utf-8")
                                        thinking_content = decoded
                                    except Exception:
                                        pass
                            elif isinstance(thinking_data, str):
                                thinking_content = thinking_data

                        message["thinking_content"] = thinking_content

                messages.append(message)

            except json.JSONDecodeError:
                continue

        return messages

    def extract_attached_files(self, bubble_data: Dict) -> List[Dict]:
        """Extract information about attached files from bubble data"""
        attached_files = []

        # 1. Active file (open in editor)
        current_file_data = bubble_data.get("currentFileLocationData")
        if current_file_data:
            # Try different fields for file path
            file_path = (
                current_file_data.get("uri")
                or current_file_data.get("path")
                or current_file_data.get("filePath")
                or current_file_data.get("file")
            )

            if file_path:
                attached_files.append(
                    {
                        "type": "active",
                        "path": file_path,
                        "line": current_file_data.get("line"),
                        "preview": current_file_data.get("preview"),
                    }
                )

        # 2. Relevant files from projectLayouts
        project_layouts = bubble_data.get("projectLayouts", [])
        for layout in project_layouts:
            # If this is a list of JSON strings
            if isinstance(layout, str):
                try:
                    layout_data = json.loads(layout)
                    if isinstance(layout_data, dict):
                        # Extract files from layout structure
                        files = self.extract_files_from_layout(layout_data)
                        for file_path in files:
                            attached_files.append(
                                {"type": "project", "path": file_path}
                            )
                except json.JSONDecodeError:
                    continue
            # If this is an object
            elif isinstance(layout, dict):
                files = self.extract_files_from_layout(layout)
                for file_path in files:
                    attached_files.append({"type": "project", "path": file_path})

        # 3. Context files with code chunks
        context_chunks = bubble_data.get("codebaseContextChunks", [])
        for chunk in context_chunks:
            if isinstance(chunk, dict):
                file_path = chunk.get("relativeWorkspacePath")
                if file_path:
                    attached_files.append(
                        {
                            "type": "context",
                            "path": file_path,
                            "content": chunk.get("contents", ""),
                            "line_range": chunk.get("lineRange"),
                        }
                    )

        # 4. Relevant files (automatically determined)
        relevant_files = bubble_data.get("relevantFiles", [])
        for file_info in relevant_files:
            if isinstance(file_info, dict):
                file_path = file_info.get("path") or file_info.get("uri")
                if file_path:
                    attached_files.append({"type": "relevant", "path": file_path})
            elif isinstance(file_info, str):
                attached_files.append({"type": "relevant", "path": file_info})

        # 5. Explicitly attached files (@-files)
        attached_chunks = bubble_data.get("attachedCodeChunks", [])
        for chunk in attached_chunks:
            if isinstance(chunk, dict):
                file_path = chunk.get("path") or chunk.get("uri")
                if file_path:
                    attached_files.append(
                        {
                            "type": "selected",
                            "path": file_path,
                            "content": chunk.get("content", ""),
                            "selection": chunk.get("selection"),
                        }
                    )

        # 6. File selections from context
        context = bubble_data.get("context", {})
        if isinstance(context, dict):
            file_selections = context.get("fileSelections", [])
            for selection in file_selections:
                if isinstance(selection, dict):
                    file_path = selection.get("path") or selection.get("uri")
                    if file_path:
                        attached_files.append(
                            {
                                "type": "selected_context",
                                "path": file_path,
                                "selection": selection.get("selection"),
                            }
                        )

        return attached_files

    def extract_files_from_layout(
        self, layout_data: Dict, current_path: str = ""
    ) -> List[str]:
        """Recursively extract all file paths from project structure"""
        files = []

        if isinstance(layout_data, dict):
            for key, value in layout_data.items():
                new_path = f"{current_path}/{key}" if current_path else key

                if isinstance(value, dict):
                    # Recursively process subdirectories
                    files.extend(self.extract_files_from_layout(value, new_path))
                elif value is None:
                    # This is a file (leaf node)
                    files.append(new_path)

        return files

    def format_attached_files(
        self, attached_files: List[Dict], max_output_lines: int
    ) -> str:
        """Format attached files for display"""
        if not attached_files:
            return ""

        # Group files by type (safely handle missing 'type' key)
        active_files = [f for f in attached_files if f.get("type") == "active"]
        selected_files = [f for f in attached_files if f.get("type") == "selected"]
        context_files = [f for f in attached_files if f.get("type") == "context"]
        relevant_files = [f for f in attached_files if f.get("type") == "relevant"]
        project_files = [f for f in attached_files if f.get("type") == "project"]
        selected_context_files = [
            f for f in attached_files if f.get("type") == "selected_context"
        ]

        result = []

        # Active files
        for file_info in active_files:
            file_path = file_info.get('path', 'unknown')
            result.append(f"   📍 Active file: {file_path}")
            if file_info.get("line"):
                result.append(f"      Line: {file_info['line']}")
            if file_info.get("preview"):
                preview = (
                    file_info["preview"][:100] + "..."
                    if len(file_info["preview"]) > 100
                    else file_info["preview"]
                )
                result.append(f"      Preview: {preview}")

        # Selected files (@-files)
        for file_info in selected_files:
            file_path = file_info.get('path', 'unknown')
            result.append(f"   ✅ Selected file: {file_path}")
            if file_info.get("selection"):
                result.append(f"      Selection: {file_info['selection']}")

        # Context files with code chunks
        for file_info in context_files:
            file_path = file_info.get('path', 'unknown')
            result.append(f"   📎 Context file: {file_path}")
            if file_info.get("line_range"):
                result.append(f"      Lines: {file_info['line_range']}")
            if file_info.get("content") and max_output_lines > 1:
                content = file_info["content"]
                if len(content) > 200:
                    content = content[:200] + "..."
                result.append(f"      Content: {content}")

        # Relevant files
        for file_info in relevant_files:
            file_path = file_info.get('path', 'unknown')
            result.append(f"   🔗 Relevant file: {file_path}")

        # Project files (limit to first 10 for readability)
        if project_files:
            result.append(f"   📁 Project files ({len(project_files)} files):")
            for i, file_info in enumerate(project_files[:10]):
                file_path = file_info.get('path', 'unknown')
                result.append(f"      - {file_path}")
            if len(project_files) > 10:
                result.append(f"      ... and {len(project_files) - 10} more files")

        # Selected context files
        for file_info in selected_context_files:
            file_path = file_info.get('path', 'unknown')
            result.append(f"   🎯 Selected in context: {file_path}")
            if file_info.get("selection"):
                result.append(f"      Selection: {file_info['selection']}")

        return "\n".join(result)

    def format_tool_call(self, tool_data: Dict, max_output_lines: int = 1) -> str:
        """Format tool call"""
        if not tool_data or (
            tool_data.get("tool") is None and not tool_data.get("name")
        ):
            return ""

        tool_type = tool_data.get("tool")
        tool_name = tool_data.get("name", "unknown")
        status = tool_data.get("status", "unknown")
        user_decision = tool_data.get("userDecision", "unknown")

        # Get icon for tool type
        tool_icon = "🔧 Unknown Tool"
        if isinstance(tool_type, int) and tool_type in self.tool_types:
            tool_icon = self.tool_types[tool_type]
        elif isinstance(tool_type, int):
            tool_icon = f"🔧 Tool {tool_type}"

        output = []
        output.append(f"🛠️ TOOL: {tool_icon}")
        output.append(f"   Name: {tool_name}")
        output.append(f"   Status: {status}")

        if user_decision != "unknown":
            decision_icon = "✅" if user_decision == "accepted" else "❌"
            output.append(f"   Decision: {decision_icon} {user_decision}")

        # Show parameters if available
        raw_args = tool_data.get("rawArgs")
        if raw_args:
            try:
                args = json.loads(raw_args)
                output.append("   Parameters:")
                for key, value in args.items():
                    if isinstance(value, str) and key == "explanation":
                        pass  # Do not truncate explanation
                    elif (
                        tool_name in ["edit_file", "search_replace"]
                        and key == "code_edit"
                    ):
                        # Apply truncation for code_edit in edit_file
                        value_lines = value.splitlines()
                        if len(value_lines) > max_output_lines:
                            value = (
                                "\n".join(value_lines[:max_output_lines])
                                + f"... ({len(value_lines) - max_output_lines} more lines)"
                            )
                        output.append(f"     {key}: {value}")
                        continue  # Skip general truncation for code_edit
                    elif isinstance(value, str) and len(value) > 70:  # general params
                        value = value[:70] + "..."
                    output.append(f"     {key}: {value}")
            except json.JSONDecodeError:
                pass

        # Show result if available
        result = tool_data.get("result")
        if result:
            try:
                result_data = json.loads(result)
                output.append("   Result:")

                # Special handling for file reading
                if tool_name == "read_file":
                    for key, value in result_data.items():
                        if key == "contents":
                            # Apply truncation only to 'contents'
                            value_lines = str(value).splitlines()
                            if len(value_lines) > max_output_lines:
                                value_str = (
                                    "\n".join(value_lines[:max_output_lines])
                                    + f"... ({len(value_lines) - max_output_lines} more lines)"
                                )
                            else:
                                value_str = str(value)
                            output.append(f"     {key}: {value_str}")
                        else:
                            # Display other fields without truncation
                            output.append(f"     {key}: {value}")

                # Special handling for terminal commands
                elif tool_name == "run_terminal_cmd":
                    cmd_output = result_data.get("output", "")
                    exit_code = result_data.get("exitCodeV2", "unknown")
                    output.append(f"     Exit code: {exit_code}")
                    if cmd_output:
                        # Apply truncation for command output
                        lines = cmd_output.splitlines()
                        if len(lines) > max_output_lines:
                            cmd_output = (
                                "\n".join(lines[:max_output_lines])
                                + f"... ({len(lines) - max_output_lines} more lines)"
                            )
                        output.append(f"     Output: {cmd_output}")

                # Special handling for file editing
                elif tool_name in ["edit_file", "search_replace"]:
                    if "diff" in result_data:
                        diff_data = result_data["diff"]
                        if "chunks" in diff_data:
                            output.append("     Changes:")
                            total_lines_added = sum(
                                chunk.get("linesAdded", 0)
                                for chunk in diff_data["chunks"]
                            )
                            total_lines_removed = sum(
                                chunk.get("linesRemoved", 0)
                                for chunk in diff_data["chunks"]
                            )

                            if max_output_lines == 1:
                                output.append(
                                    f"       +{total_lines_added} -{total_lines_removed} "
                                    "lines (details hidden)"
                                )
                            else:
                                # Show detailed diff chunks up to max_output_lines
                                lines_shown = 0
                                for chunk in diff_data["chunks"]:
                                    if lines_shown >= max_output_lines:
                                        break
                                    diff_string = chunk.get("diffString", "")
                                    chunk_lines = diff_string.splitlines()
                                    lines_to_show = min(
                                        len(chunk_lines), max_output_lines - lines_shown
                                    )

                                    for line in chunk_lines[:lines_to_show]:
                                        output.append(f"       {line}")
                                    lines_shown += lines_to_show

                                    if len(chunk_lines) > lines_to_show:  # more lines
                                        output.append(
                                            f"       ... ({len(chunk_lines) - lines_to_show} "
                                            "more lines in chunk)"
                                        )

                                if (
                                    total_lines_added + total_lines_removed
                                    > lines_shown
                                ):  # Indicate total more lines
                                    output.append(
                                        f"       ... (Total changes: +{total_lines_added} "
                                        f"-{total_lines_removed} lines)"
                                    )

                # For other tools show brief information
                else:
                    # Apply truncation for other results
                    if isinstance(result_data, dict):
                        items = list(result_data.items())
                        if len(items) > max_output_lines:
                            output.append(
                                f"     (Showing {max_output_lines} of {len(items)} fields)"
                            )
                            items = items[:max_output_lines]
                        for key, value in items:
                            value_str = str(value)
                            if len(value_str) > 70:  # Reduce character limit
                                value_str = value_str[:70] + "..."
                            output.append(f"     {key}: {value_str}")
                    else:
                        result_str = str(result_data)
                        lines = result_str.splitlines()
                        if len(lines) > max_output_lines:
                            result_str = (
                                "\n".join(lines[:max_output_lines])
                                + f"... ({len(lines) - max_output_lines} more lines)"
                            )
                        output.append(f"     {result_str}")

            except json.JSONDecodeError:
                pass

        return "\n".join(output)

    def format_token_info(self, message: Dict) -> str:
        """Format token usage and metadata information for a message"""
        token_count = message.get("token_count", {})
        usage_uuid = message.get("usage_uuid")
        server_bubble_id = message.get("server_bubble_id")
        is_agentic = message.get("is_agentic", False)
        capabilities_ran = message.get("capabilities_ran", {})
        unified_mode = message.get("unified_mode")
        use_web = message.get("use_web", False)
        is_refunded = message.get("is_refunded", False)

        if not any(
            [
                token_count,
                usage_uuid,
                server_bubble_id,
                is_agentic,
                capabilities_ran,
                unified_mode,
                use_web,
                is_refunded,
            ]
        ):
            return ""

        output = []

        # Token information and model inference
        if token_count:
            input_tokens = token_count.get("inputTokens", 0)
            output_tokens = token_count.get("outputTokens", 0)
            total_tokens = input_tokens + output_tokens

            if total_tokens > 0:
                # Infer model based on context
                inferred_model = self.infer_model_from_context(message, total_tokens)
                output.append(
                    f"🔢 Tokens: {input_tokens}→{output_tokens} ({total_tokens} total)"
                )
                if inferred_model:
                    output.append(f"🤖 Inferred model: {inferred_model}")

        # Agentic mode indicator
        if is_agentic:
            output.append("🧠 Agentic mode: enabled")

        # Unified mode
        if unified_mode:
            output.append(f"🔄 Unified mode: {unified_mode}")

        # Web usage
        if use_web:
            output.append("🌐 Web search: used")

        # Capabilities
        if capabilities_ran:
            cap_list = list(capabilities_ran.keys())
            if cap_list:
                output.append(f"⚙️ Capabilities: {', '.join(cap_list[:3])}")
                if len(cap_list) > 3:
                    output.append(f"   ... and {len(cap_list) - 3} more")

        # Refund status
        if is_refunded:
            output.append("💰 Status: refunded")

        # Usage UUID (for debugging)
        if usage_uuid:
            output.append(f"🔍 Usage ID: {usage_uuid[:8]}...")

        return "\n".join(output)

    def infer_model_from_context(self, message: Dict, total_tokens: int) -> str:
        """Infer likely model based on context clues and usage patterns"""
        # Check for explicit model mentions in text
        text = message.get("text", "").lower()
        if "claude" in text or "sonnet" in text:
            return "Claude (mentioned in text)"
        elif "gpt" in text or "openai" in text:
            return "GPT (mentioned in text)"
        elif "o1" in text:
            return "OpenAI o1 (mentioned in text)"

        # Check agentic mode (typically Claude)
        if message.get("is_agentic"):
            return "Claude (agentic mode)"

        # Check token usage patterns
        if total_tokens > 100000:  # Very high token usage
            return "Claude (high token usage)"
        elif total_tokens > 32000:  # High token usage
            return "GPT-4 or Claude (high token usage)"

        # Check unified mode patterns
        unified_mode = message.get("unified_mode")
        if unified_mode == 4:
            return "Advanced model (unified mode 4)"
        elif unified_mode == 2:
            return "Standard model (unified mode 2)"

        # Check capabilities for complexity
        capabilities = message.get("capabilities_ran", {})
        if len(capabilities) > 5:
            return "Advanced model (complex capabilities)"

        return ""  # Cannot infer

    def format_dialog(
        self,
        messages: List[Dict],
        dialog_name: str,
        project_name: str,
        max_output_lines: int,
    ) -> str:
        """Format dialog for display"""
        output = []
        output.append("=" * 60)
        output.append(f"PROJECT: {project_name}")
        output.append(f"DIALOG: {dialog_name}")
        output.append("=" * 60)
        output.append("")

        for i, message in enumerate(messages):
            message_type = message.get("type")
            text = message.get("text", "").strip()
            tool_data = message.get("tool_data")
            attached_files = message.get("attached_files", [])
            is_thought = message.get("is_thought", False)
            thinking_duration = message.get("thinking_duration", 0)
            thinking_content = message.get("thinking_content", "")

            # Skip empty messages without tools or attachments
            if not text and not tool_data and not attached_files and not is_thought:
                continue

            # AI thinking bubble
            if is_thought:
                output.append("🧠 AI THINKING:")
                if thinking_duration > 0:
                    output.append(f"   Duration: {thinking_duration/1000:.1f}s")
                if thinking_content:
                    # Truncate thinking content if too long
                    if len(thinking_content) > 500:
                        thinking_content = thinking_content[:500] + "..."
                    output.append(f"   Content: {thinking_content}")
                output.append("-" * 40)
                continue

            # User message
            if message_type == 1:
                output.append("👤 USER:")
                if text:
                    output.append(text)

                # Show attached files
                if attached_files:
                    output.append("")
                    output.append("📎 ATTACHED FILES:")
                    attached_output = self.format_attached_files(
                        attached_files, max_output_lines
                    )
                    output.append(attached_output)

                output.append("-" * 40)

            # AI response
            elif message_type == 2:
                # Show tool call first if present
                if tool_data:
                    tool_output = self.format_tool_call(tool_data, max_output_lines)
                    if tool_output:
                        output.append(tool_output)
                        output.append("-" * 40)

                # Then show AI response
                if text:
                    output.append("🤖 AI:")
                    output.append(text)

                    # Show token info and metadata
                    token_info = self.format_token_info(message)
                    if token_info:
                        output.append("")
                        output.append(token_info)

                    output.append("-" * 40)

            # Other message types
            else:
                if text or tool_data:
                    output.append(f"📝 MESSAGE (type {message_type}):")
                    if text:
                        output.append(text)

                    if tool_data:
                        tool_output = self.format_tool_call(tool_data, max_output_lines)
                        if tool_output:
                            output.append(tool_output)

                    output.append("-" * 40)

        return "\n".join(output)

    def list_projects(self):
        """Show list of all projects"""
        projects = self.get_projects()

        if not projects:
            print("No projects found.")
            return

        print("Available projects:")
        print("=" * 50)

        for project in projects:
            print(f"📁 {project['project_name']}")
            print(f"   Path: {project['folder_path']}")
            print(f"   Dialogs: {len(project['composers'])}")

            if project["latest_dialog"]:
                latest = project["latest_dialog"]
                name = latest.get("name", "Untitled")
                timestamp = latest.get("lastUpdatedAt", 0)
                if timestamp:
                    date = datetime.fromtimestamp(timestamp / 1000)
                    print(f"   Latest: {name} ({date.strftime('%Y-%m-%d %H:%M')})")

            print()

    def list_dialogs(self, project_name: str):
        """Show list of dialogs for project"""
        projects = self.get_projects()

        # Find project
        project = None
        for p in projects:
            if project_name.lower() in p["project_name"].lower():
                project = p
                break

        if not project:
            print(f"Project '{project_name}' not found.")
            return

        composers = project["composers"]
        if not composers:
            print(f"No dialogs found in project '{project['project_name']}'.")
            return

        print(f"Dialogs in project '{project['project_name']}':")
        print("=" * 50)

        # Sort by last updated time
        composers.sort(key=lambda x: x.get("lastUpdatedAt", 0), reverse=True)

        for composer in composers:
            name = composer.get("name", "Untitled")
            composer_id = composer.get("composerId", "unknown")
            timestamp = composer.get("lastUpdatedAt", 0)

            if timestamp:
                date = datetime.fromtimestamp(timestamp / 1000)
                print(f"💬 {name}")
                print(f"   ID: {composer_id}")
                print(f"   Updated: {date.strftime('%Y-%m-%d %H:%M')}")
            else:
                print(f"💬 {name} (ID: {composer_id})")

            print()

    def get_all_dialogs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        project_filter: Optional[str] = None,
        sort_by: str = "date",
        sort_desc: bool = False,
    ) -> List[Dict]:
        """
        Get all dialogs across all projects, optionally filtered by time interval.
        
        Args:
            start_date: Filter dialogs updated after this date (inclusive)
            end_date: Filter dialogs updated before this date (inclusive)
            project_filter: Filter by project name (partial match)
            sort_by: Sort field - "date", "name", or "project"
            sort_desc: Sort descending if True, ascending if False (default)
        
        Returns:
            List of dialog info dicts with project context
        """
        projects = self.get_projects()
        all_dialogs = []

        # Convert dates to milliseconds timestamp if provided
        start_ts = int(start_date.timestamp() * 1000) if start_date else None
        end_ts = int(end_date.timestamp() * 1000) if end_date else None

        for project in projects:
            # Apply project filter
            if project_filter:
                if project_filter.lower() not in project["project_name"].lower():
                    continue

            for composer in project.get("composers", []):
                timestamp = composer.get("lastUpdatedAt", 0)
                created_at = composer.get("createdAt", 0)

                # Apply time filters
                if start_ts and timestamp < start_ts:
                    continue
                if end_ts and timestamp > end_ts:
                    continue

                all_dialogs.append({
                    "composer_id": composer.get("composerId", "unknown"),
                    "name": composer.get("name", "Untitled"),
                    "project_name": project["project_name"],
                    "folder_path": project["folder_path"],
                    "last_updated": timestamp,
                    "created_at": created_at,
                })

        # Sort by specified field
        if sort_by == "name":
            all_dialogs.sort(
                key=lambda x: x.get("name", "").lower(),
                reverse=sort_desc
            )
        elif sort_by == "project":
            all_dialogs.sort(
                key=lambda x: (x.get("project_name", "").lower(), x.get("name", "").lower()),
                reverse=sort_desc
            )
        else:  # date (default)
            all_dialogs.sort(
                key=lambda x: x.get("last_updated", 0),
                reverse=sort_desc
            )
        return all_dialogs

    def list_all_dialogs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        project_filter: Optional[str] = None,
        limit: int = 50,
        sort_by: str = "date",
        sort_desc: bool = False,
    ):
        """
        Display all dialogs across all projects with optional time filtering.
        
        Args:
            start_date: Filter dialogs updated after this date
            end_date: Filter dialogs updated before this date
            project_filter: Filter by project name (partial match)
            limit: Maximum number of dialogs to display
            sort_by: Sort field - "date", "name", or "project"
            sort_desc: Sort descending if True, ascending if False (default)
        """
        dialogs = self.get_all_dialogs(
            start_date, end_date, project_filter, sort_by, sort_desc
        )

        if not dialogs:
            date_info = ""
            if start_date or end_date:
                if start_date and end_date:
                    date_info = f" between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}"
                elif start_date:
                    date_info = f" after {start_date.strftime('%Y-%m-%d')}"
                else:
                    date_info = f" before {end_date.strftime('%Y-%m-%d')}"
            print(f"No dialogs found{date_info}.")
            return

        # Build header with filter info
        header_parts = ["All dialogs"]
        if project_filter:
            header_parts.append(f"in '{project_filter}'")
        if start_date or end_date:
            if start_date and end_date:
                header_parts.append(
                    f"from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                )
            elif start_date:
                header_parts.append(f"after {start_date.strftime('%Y-%m-%d')}")
            else:
                header_parts.append(f"before {end_date.strftime('%Y-%m-%d')}")

        print(" ".join(header_parts) + ":")
        print(f"Found {len(dialogs)} dialog(s)")
        print("=" * 60)

        displayed = 0
        for dialog in dialogs:
            if displayed >= limit:
                remaining = len(dialogs) - limit
                print(f"... and {remaining} more dialogs (use --limit to see more)")
                break

            name = dialog["name"]
            composer_id = dialog["composer_id"]
            project_name = dialog["project_name"]
            timestamp = dialog["last_updated"]
            created_at = dialog["created_at"]

            print(f"💬 {name}")
            print(f"   📁 Project: {project_name}")
            print(f"   🔗 ID: {composer_id}")

            if timestamp:
                date = datetime.fromtimestamp(timestamp / 1000)
                print(f"   📅 Updated: {date.strftime('%Y-%m-%d %H:%M')}")
            if created_at:
                date = datetime.fromtimestamp(created_at / 1000)
                print(f"   📅 Created: {date.strftime('%Y-%m-%d %H:%M')}")

            print()
            displayed += 1

    def show_dialog(
        self,
        project_name: Optional[str] = None,
        dialog_name: Optional[str] = None,
        max_output_lines: int = 1,
    ):
        """Show dialog"""
        projects = self.get_projects()

        if not projects:
            print("No projects found.")
            return

        # Find project
        project = None
        if project_name:
            for p in projects:
                if project_name.lower() in p["project_name"].lower():
                    project = p
                    break

            if not project:
                print(f"Project '{project_name}' not found.")
                return
        else:
            # Use most recent project
            project = projects[0]

        # Find dialog
        composer = None
        if dialog_name:
            for c in project["composers"]:
                c_name = c.get("name", "").lower()
                if dialog_name.lower() in c_name:
                    composer = c
                    break

            if not composer:
                print(
                    f"Dialog '{dialog_name}' not found in project '{project['project_name']}'."
                )
                return
        else:
            # Use most recent dialog
            if project["composers"]:
                composer = max(
                    project["composers"], key=lambda x: x.get("lastUpdatedAt", 0)
                )
            else:
                print(f"No dialogs found in project '{project['project_name']}'.")
                return

        # Get dialog messages
        composer_id = composer.get("composerId")
        if not composer_id:
            print("Dialog ID not found.")
            return

        try:
            messages = self.get_dialog_messages(composer_id)

            if not messages:
                print("No messages found in dialog.")
                return

            # Display dialog
            dialog_output = self.format_dialog(
                messages,
                composer.get("name", "Untitled"),
                project["project_name"],
                max_output_lines,
            )
            print(dialog_output)

        except Exception as e:
            print(f"Error reading dialog: {e}")


def parse_date(date_str: str) -> datetime:
    """Parse date string in various formats"""
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"Invalid date format: {date_str}. Use YYYY-MM-DD or similar."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Cursor Chronicle - View Cursor IDE chat history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-projects              # List all projects
  %(prog)s --list-dialogs myproject     # List dialogs in project
  %(prog)s --list-all                   # List all dialogs (oldest first)
  %(prog)s --list-all --desc            # List all dialogs (newest first)
  %(prog)s --list-all --from 2024-01-01 # Dialogs after date
  %(prog)s --list-all --to 2024-12-31   # Dialogs before date
  %(prog)s --list-all --sort name       # Sort by dialog name (A-Z)
  %(prog)s --list-all --sort project    # Sort by project name (A-Z)
  %(prog)s --list-all -p myproject      # All dialogs filtered by project
  %(prog)s -p myproject -d "my chat"    # Show specific dialog
        """,
    )
    parser.add_argument(
        "--project", "-p", help="Project name (partial match supported)"
    )
    parser.add_argument("--dialog", "-d", help="Dialog name (partial match supported)")
    parser.add_argument(
        "--list-projects", action="store_true", help="Show list of projects"
    )
    parser.add_argument("--list-dialogs", help="Show list of dialogs for project")
    parser.add_argument(
        "--list-all",
        action="store_true",
        help="List all dialogs across all projects",
    )
    parser.add_argument(
        "--from",
        dest="start_date",
        type=parse_date,
        help="Filter dialogs updated after this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--to",
        dest="end_date",
        type=parse_date,
        help="Filter dialogs updated before this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum dialogs to display (default: 50)",
    )
    parser.add_argument(
        "--sort",
        choices=["date", "name", "project"],
        default="date",
        help="Sort dialogs by: date, name, or project (default: date)",
    )
    parser.add_argument(
        "--desc",
        action="store_true",
        help="Sort descending (newest/Z first). Default is ascending (oldest/A first)",
    )
    parser.add_argument(
        "--max-output-lines",
        type=int,
        default=1,
        help="Maximum lines to show for tool outputs (default: 1)",
    )

    args = parser.parse_args()

    viewer = CursorChatViewer()

    if args.list_projects:
        viewer.list_projects()
    elif args.list_dialogs:
        viewer.list_dialogs(args.list_dialogs)
    elif args.list_all:
        viewer.list_all_dialogs(
            start_date=args.start_date,
            end_date=args.end_date,
            project_filter=args.project,
            limit=args.limit,
            sort_by=args.sort,
            sort_desc=args.desc,
        )
    else:
        viewer.show_dialog(args.project, args.dialog, args.max_output_lines)


if __name__ == "__main__":
    main()
