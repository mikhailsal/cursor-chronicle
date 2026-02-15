"""
Output formatting functions for Cursor Chronicle.
"""

import json
from typing import Dict, List

from .utils import TOOL_TYPES


def format_attached_files(attached_files: List[Dict], max_output_lines: int) -> str:
    """Format attached files for display."""
    if not attached_files:
        return ""

    active_files = [f for f in attached_files if f.get("type") == "active"]
    selected_files = [f for f in attached_files if f.get("type") == "selected"]
    context_files = [f for f in attached_files if f.get("type") == "context"]
    relevant_files = [f for f in attached_files if f.get("type") == "relevant"]
    project_files = [f for f in attached_files if f.get("type") == "project"]
    selected_context_files = [
        f for f in attached_files if f.get("type") == "selected_context"
    ]

    result = []

    for file_info in active_files:
        file_path = file_info.get('path', 'unknown')
        result.append(f"   📍 Active file: {file_path}")
        if file_info.get("line"):
            result.append(f"      Line: {file_info['line']}")
        if file_info.get("preview"):
            preview = file_info["preview"][:100] + "..." if len(file_info["preview"]) > 100 else file_info["preview"]
            result.append(f"      Preview: {preview}")

    for file_info in selected_files:
        file_path = file_info.get('path', 'unknown')
        result.append(f"   ✅ Selected file: {file_path}")
        if file_info.get("selection"):
            result.append(f"      Selection: {file_info['selection']}")

    for file_info in context_files:
        file_path = file_info.get('path', 'unknown')
        result.append(f"   📎 Context file: {file_path}")
        if file_info.get("line_range"):
            result.append(f"      Lines: {file_info['line_range']}")
        if file_info.get("content") and max_output_lines > 1:
            content = file_info["content"][:200] + "..." if len(file_info["content"]) > 200 else file_info["content"]
            result.append(f"      Content: {content}")

    for file_info in relevant_files:
        file_path = file_info.get('path', 'unknown')
        result.append(f"   🔗 Relevant file: {file_path}")

    if project_files:
        result.append(f"   📁 Project files ({len(project_files)} files):")
        for file_info in project_files[:10]:
            file_path = file_info.get('path', 'unknown')
            result.append(f"      - {file_path}")
        if len(project_files) > 10:
            result.append(f"      ... and {len(project_files) - 10} more files")

    for file_info in selected_context_files:
        file_path = file_info.get('path', 'unknown')
        result.append(f"   🎯 Selected in context: {file_path}")
        if file_info.get("selection"):
            result.append(f"      Selection: {file_info['selection']}")

    return "\n".join(result)


def format_tool_call(tool_data: Dict, max_output_lines: int = 1) -> str:
    """Format tool call for display."""
    if not tool_data or (tool_data.get("tool") is None and not tool_data.get("name")):
        return ""

    tool_type = tool_data.get("tool")
    tool_name = tool_data.get("name", "unknown")
    status = tool_data.get("status", "unknown")
    user_decision = tool_data.get("userDecision", "unknown")

    tool_icon = "🔧 Unknown Tool"
    if isinstance(tool_type, int) and tool_type in TOOL_TYPES:
        tool_icon = TOOL_TYPES[tool_type]
    elif isinstance(tool_type, int):
        tool_icon = f"🔧 Tool {tool_type}"

    output = []
    output.append(f"🛠️ TOOL: {tool_icon}")
    output.append(f"   Name: {tool_name}")
    output.append(f"   Status: {status}")

    if user_decision != "unknown":
        decision_icon = "✅" if user_decision == "accepted" else "❌"
        output.append(f"   Decision: {decision_icon} {user_decision}")

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
                output.append("   Parameters:")
                for key, value in args.items():
                    if isinstance(value, str) and key == "explanation":
                        pass
                    elif tool_name in ["edit_file", "search_replace"] and key == "code_edit":
                        value_lines = value.splitlines()
                        if len(value_lines) > max_output_lines:
                            value = "\n".join(value_lines[:max_output_lines]) + f"... ({len(value_lines) - max_output_lines} more lines)"
                        output.append(f"     {key}: {value}")
                        continue
                    elif isinstance(value, str) and len(value) > 70:
                        value = value[:70] + "..."
                    output.append(f"     {key}: {value}")
        except (json.JSONDecodeError, TypeError):
            pass

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
                output.append("   Result:")
                output.extend(_format_tool_result(tool_name, result_data, max_output_lines))
        except (json.JSONDecodeError, TypeError):
            pass

    return "\n".join(output)


def _format_tool_result(tool_name: str, result_data, max_output_lines: int) -> List[str]:
    """Format tool result based on tool type."""
    output = []

    if tool_name == "read_file":
        for key, value in result_data.items():
            if key == "contents":
                value_lines = str(value).splitlines()
                if len(value_lines) > max_output_lines:
                    value_str = "\n".join(value_lines[:max_output_lines]) + f"... ({len(value_lines) - max_output_lines} more lines)"
                else:
                    value_str = str(value)
                output.append(f"     {key}: {value_str}")
            else:
                output.append(f"     {key}: {value}")

    elif tool_name == "run_terminal_cmd":
        cmd_output = result_data.get("output", "")
        exit_code = result_data.get("exitCodeV2", "unknown")
        output.append(f"     Exit code: {exit_code}")
        if cmd_output:
            lines = cmd_output.splitlines()
            if len(lines) > max_output_lines:
                cmd_output = "\n".join(lines[:max_output_lines]) + f"... ({len(lines) - max_output_lines} more lines)"
            output.append(f"     Output: {cmd_output}")

    elif tool_name in ["edit_file", "search_replace"]:
        if "diff" in result_data:
            diff_data = result_data["diff"]
            if "chunks" in diff_data:
                output.append("     Changes:")
                total_added = sum(chunk.get("linesAdded", 0) for chunk in diff_data["chunks"])
                total_removed = sum(chunk.get("linesRemoved", 0) for chunk in diff_data["chunks"])

                if max_output_lines == 1:
                    output.append(f"       +{total_added} -{total_removed} lines (details hidden)")
                else:
                    lines_shown = 0
                    for chunk in diff_data["chunks"]:
                        if lines_shown >= max_output_lines:
                            break
                        diff_string = chunk.get("diffString", "")
                        chunk_lines = diff_string.splitlines()
                        lines_to_show = min(len(chunk_lines), max_output_lines - lines_shown)

                        for line in chunk_lines[:lines_to_show]:
                            output.append(f"       {line}")
                        lines_shown += lines_to_show

                        if len(chunk_lines) > lines_to_show:
                            output.append(f"       ... ({len(chunk_lines) - lines_to_show} more lines in chunk)")

                    if total_added + total_removed > lines_shown:
                        output.append(f"       ... (Total changes: +{total_added} -{total_removed} lines)")
    else:
        if isinstance(result_data, dict):
            items = list(result_data.items())
            if len(items) > max_output_lines:
                output.append(f"     (Showing {max_output_lines} of {len(items)} fields)")
                items = items[:max_output_lines]
            for key, value in items:
                value_str = str(value)[:70] + "..." if len(str(value)) > 70 else str(value)
                output.append(f"     {key}: {value_str}")
        else:
            result_str = str(result_data)
            lines = result_str.splitlines()
            if len(lines) > max_output_lines:
                result_str = "\n".join(lines[:max_output_lines]) + f"... ({len(lines) - max_output_lines} more lines)"
            output.append(f"     {result_str}")

    return output


def format_token_info(message: Dict) -> str:
    """Format token usage and metadata information."""
    token_count = message.get("token_count", {})
    usage_uuid = message.get("usage_uuid")
    is_agentic = message.get("is_agentic", False)
    capabilities_ran = message.get("capabilities_ran", {})
    unified_mode = message.get("unified_mode")
    use_web = message.get("use_web", False)
    is_refunded = message.get("is_refunded", False)

    if not any([token_count, usage_uuid, is_agentic, capabilities_ran, unified_mode, use_web, is_refunded]):
        return ""

    output = []

    if token_count:
        input_tokens = token_count.get("inputTokens", 0)
        output_tokens = token_count.get("outputTokens", 0)
        total_tokens = input_tokens + output_tokens

        if total_tokens > 0:
            inferred_model = infer_model_from_context(message, total_tokens)
            output.append(f"🔢 Tokens: {input_tokens}→{output_tokens} ({total_tokens} total)")
            if inferred_model:
                output.append(f"🤖 Inferred model: {inferred_model}")

    if is_agentic:
        output.append("🧠 Agentic mode: enabled")
    if unified_mode:
        output.append(f"🔄 Unified mode: {unified_mode}")
    if use_web:
        output.append("🌐 Web search: used")
    if capabilities_ran:
        cap_list = list(capabilities_ran.keys())
        if cap_list:
            output.append(f"⚙️ Capabilities: {', '.join(cap_list[:3])}")
            if len(cap_list) > 3:
                output.append(f"   ... and {len(cap_list) - 3} more")
    if is_refunded:
        output.append("💰 Status: refunded")
    if usage_uuid:
        output.append(f"🔍 Usage ID: {usage_uuid[:8]}...")

    return "\n".join(output)


def infer_model_from_context(message: Dict, total_tokens: int) -> str:
    """Infer likely model based on context clues."""
    text = message.get("text", "").lower()
    if "claude" in text or "sonnet" in text:
        return "Claude (mentioned in text)"
    elif "gpt" in text or "openai" in text:
        return "GPT (mentioned in text)"
    elif "o1" in text:
        return "OpenAI o1 (mentioned in text)"

    if message.get("is_agentic"):
        return "Claude (agentic mode)"

    if total_tokens > 100000:
        return "Claude (high token usage)"
    elif total_tokens > 32000:
        return "GPT-4 or Claude (high token usage)"

    unified_mode = message.get("unified_mode")
    if unified_mode == 4:
        return "Advanced model (unified mode 4)"
    elif unified_mode == 2:
        return "Standard model (unified mode 2)"

    capabilities = message.get("capabilities_ran", {})
    if len(capabilities) > 5:
        return "Advanced model (complex capabilities)"

    return ""


def format_dialog(
    messages: List[Dict],
    dialog_name: str,
    project_name: str,
    max_output_lines: int,
) -> str:
    """Format dialog for display."""
    output = []
    output.append("=" * 60)
    output.append(f"PROJECT: {project_name}")
    output.append(f"DIALOG: {dialog_name}")
    output.append("=" * 60)
    output.append("")

    for message in messages:
        message_type = message.get("type")
        text = message.get("text", "").strip()
        tool_data = message.get("tool_data")
        attached_files = message.get("attached_files", [])
        is_thought = message.get("is_thought", False)
        thinking_duration = message.get("thinking_duration", 0)
        thinking_content = message.get("thinking_content", "")

        if not text and not tool_data and not attached_files and not is_thought:
            continue

        if is_thought:
            output.append("🧠 AI THINKING:")
            if thinking_duration > 0:
                output.append(f"   Duration: {thinking_duration/1000:.1f}s")
            if thinking_content:
                content = thinking_content[:500] + "..." if len(thinking_content) > 500 else thinking_content
                output.append(f"   Content: {content}")
            output.append("-" * 40)
            continue

        if message_type == 1:
            output.append("👤 USER:")
            if text:
                output.append(text)
            if attached_files:
                output.append("")
                output.append("📎 ATTACHED FILES:")
                output.append(format_attached_files(attached_files, max_output_lines))
            output.append("-" * 40)

        elif message_type == 2:
            if tool_data:
                tool_output = format_tool_call(tool_data, max_output_lines)
                if tool_output:
                    output.append(tool_output)
                    output.append("-" * 40)
            if text:
                output.append("🤖 AI:")
                output.append(text)
                token_info = format_token_info(message)
                if token_info:
                    output.append("")
                    output.append(token_info)
                output.append("-" * 40)

        else:
            if text or tool_data:
                output.append(f"📝 MESSAGE (type {message_type}):")
                if text:
                    output.append(text)
                if tool_data:
                    tool_output = format_tool_call(tool_data, max_output_lines)
                    if tool_output:
                        output.append(tool_output)
                output.append("-" * 40)

    return "\n".join(output)
