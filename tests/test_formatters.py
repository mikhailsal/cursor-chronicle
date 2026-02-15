"""
Tests for formatters.py module - output formatting functions.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cursor_chronicle


class TestFormatAttachedFiles(unittest.TestCase):
    """Test format_attached_files function."""

    def test_format_attached_files_empty(self):
        """Test with empty files."""
        result = cursor_chronicle.format_attached_files([], 1)
        self.assertEqual(result, "")

    def test_format_attached_files_basic(self):
        """Test with sample files."""
        attached_files = [
            {"type": "active", "path": "src/main.py", "line": 42},
            {"type": "selected", "path": "src/utils.py"},
        ]
        result = cursor_chronicle.format_attached_files(attached_files, 1)
        self.assertIn("Active file: src/main.py", result)
        self.assertIn("Selected file: src/utils.py", result)
        self.assertIn("Line: 42", result)

    def test_format_attached_files_with_preview(self):
        """Test active file with preview."""
        files = [{"type": "active", "path": "/test.py", "preview": "def function(): pass"}]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("Preview:", result)
        self.assertIn("def function():", result)

    def test_format_attached_files_long_preview(self):
        """Test active file with long preview (truncated)."""
        long_preview = "x" * 200
        files = [{"type": "active", "path": "/test.py", "preview": long_preview}]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("...", result)

    def test_format_attached_files_selected_with_selection(self):
        """Test selected file with selection info."""
        files = [{"type": "selected", "path": "/test.py", "selection": "1-10"}]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("Selection: 1-10", result)

    def test_format_attached_files_context_with_content(self):
        """Test context file with content."""
        files = [{"type": "context", "path": "/test.py", "line_range": "10-20", "content": "def test():"}]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("Lines: 10-20", result)
        self.assertIn("Content:", result)

    def test_format_attached_files_context_long_content(self):
        """Test context file with long content (truncated)."""
        long_content = "x" * 300
        files = [{"type": "context", "path": "/test.py", "content": long_content}]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("...", result)

    def test_format_attached_files_many_project_files(self):
        """Test many project files (truncated list)."""
        files = [{"type": "project", "path": f"/file{i}.py"} for i in range(20)]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("20 files", result)
        self.assertIn("and 10 more files", result)

    def test_format_attached_files_selected_context(self):
        """Test selected context files."""
        files = [{"type": "selected_context", "path": "/test.py", "selection": "5-15"}]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("Selected in context:", result)
        self.assertIn("Selection: 5-15", result)

    def test_format_attached_files_missing_path(self):
        """Test files with missing path field."""
        files = [{"type": "active"}]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("unknown", result)


class TestFormatToolCall(unittest.TestCase):
    """Test format_tool_call function."""

    def test_format_tool_call_empty(self):
        """Test with empty tool data."""
        result = cursor_chronicle.format_tool_call({}, 1)
        self.assertEqual(result, "")

    def test_format_tool_call_null_tool(self):
        """Test with null tool field."""
        result = cursor_chronicle.format_tool_call({"tool": None}, 1)
        self.assertEqual(result, "")

    def test_format_tool_call_basic(self):
        """Test basic tool call formatting."""
        tool_data = {"tool": 5, "name": "read_file", "status": "completed", "userDecision": "accepted"}
        result = cursor_chronicle.format_tool_call(tool_data, 1)
        self.assertIn("TOOL", result)
        self.assertIn("Read File", result)
        self.assertIn("read_file", result)
        self.assertIn("completed", result)
        self.assertIn("✅", result)

    def test_format_tool_call_rejected(self):
        """Test tool call with rejected decision."""
        tool_data = {"tool": 7, "name": "edit_file", "status": "completed", "userDecision": "rejected"}
        result = cursor_chronicle.format_tool_call(tool_data, 1)
        self.assertIn("❌", result)

    def test_format_tool_call_unknown_tool_type(self):
        """Test with unknown tool type."""
        tool_data = {"tool": 999, "name": "unknown_tool", "status": "completed"}
        result = cursor_chronicle.format_tool_call(tool_data, 1)
        self.assertIn("Tool 999", result)

    def test_format_tool_call_with_raw_args(self):
        """Test tool call with raw arguments."""
        tool_data = {"tool": 5, "name": "read_file", "status": "completed", "rawArgs": json.dumps({"path": "/path/to/file.py"})}
        result = cursor_chronicle.format_tool_call(tool_data, 1)
        self.assertIn("path", result)
        self.assertIn("/path/to/file.py", result)

    def test_format_tool_call_with_explanation(self):
        """Test tool call with explanation (not truncated)."""
        long_explanation = "x" * 200
        tool_data = {"tool": 5, "name": "read_file", "status": "completed", "rawArgs": json.dumps({"explanation": long_explanation})}
        result = cursor_chronicle.format_tool_call(tool_data, 1)
        self.assertIn(long_explanation, result)

    def test_format_tool_call_code_edit_truncation(self):
        """Test code_edit truncation in edit_file."""
        code_edit = "\n".join([f"line {i}" for i in range(100)])
        tool_data = {"tool": 7, "name": "edit_file", "status": "completed", "rawArgs": json.dumps({"code_edit": code_edit})}
        result = cursor_chronicle.format_tool_call(tool_data, 5)
        self.assertIn("more lines", result)

    def test_format_tool_call_long_param_truncation(self):
        """Test long parameter truncation."""
        long_value = "x" * 200
        tool_data = {"tool": 5, "name": "read_file", "status": "completed", "rawArgs": json.dumps({"path": long_value})}
        result = cursor_chronicle.format_tool_call(tool_data, 1)
        self.assertIn("...", result)

    def test_format_tool_call_read_file_result(self):
        """Test read_file result formatting."""
        contents = "\n".join([f"line {i}" for i in range(100)])
        tool_data = {"tool": 5, "name": "read_file", "status": "completed", "result": json.dumps({"contents": contents, "file": "/test.py"})}
        result = cursor_chronicle.format_tool_call(tool_data, 5)
        self.assertIn("more lines", result)
        self.assertIn("file", result)

    def test_format_tool_call_terminal_cmd_result(self):
        """Test run_terminal_cmd result formatting."""
        output = "\n".join([f"output line {i}" for i in range(100)])
        tool_data = {"tool": 15, "name": "run_terminal_cmd", "status": "completed", "result": json.dumps({"output": output, "exitCodeV2": 0})}
        result = cursor_chronicle.format_tool_call(tool_data, 5)
        self.assertIn("Exit code: 0", result)
        self.assertIn("more lines", result)

    def test_format_tool_call_edit_file_diff_result(self):
        """Test edit_file diff result formatting."""
        tool_data = {
            "tool": 7,
            "name": "edit_file",
            "status": "completed",
            "result": json.dumps({"diff": {"chunks": [{"linesAdded": 5, "linesRemoved": 3, "diffString": "+new\n-old"}]}}),
        }
        result1 = cursor_chronicle.format_tool_call(tool_data, 1)
        self.assertIn("+5 -3", result1)
        self.assertIn("details hidden", result1)

        result2 = cursor_chronicle.format_tool_call(tool_data, 10)
        self.assertIn("+new", result2)


class TestFormatToolCallDictTypes(unittest.TestCase):
    """Test format_tool_call with dict-typed rawArgs and result (not JSON strings)."""

    def test_dict_raw_args(self):
        """Test tool call when rawArgs is already a dict."""
        tool_data = {
            "tool": 5,
            "name": "read_file",
            "status": "completed",
            "rawArgs": {"path": "/path/to/file.py"},  # dict, not JSON string
        }
        result = cursor_chronicle.format_tool_call(tool_data, 1)
        self.assertIn("path", result)
        self.assertIn("/path/to/file.py", result)

    def test_dict_result(self):
        """Test tool call when result is already a dict."""
        tool_data = {
            "tool": 5,
            "name": "read_file",
            "status": "completed",
            "result": {"contents": "hello world", "file": "/test.py"},  # dict, not JSON string
        }
        result = cursor_chronicle.format_tool_call(tool_data, 5)
        self.assertIn("Result", result)
        self.assertIn("hello world", result)

    def test_list_result(self):
        """Test tool call when result is a list."""
        tool_data = {
            "tool": 5,
            "name": "some_tool",
            "status": "completed",
            "result": [{"file": "a.py"}, {"file": "b.py"}],  # list, not JSON string
        }
        result = cursor_chronicle.format_tool_call(tool_data, 5)
        self.assertIn("Result", result)

    def test_unexpected_rawargs_type(self):
        """Test tool call when rawArgs is an unexpected type (e.g., int)."""
        tool_data = {
            "tool": 5,
            "name": "some_tool",
            "status": "completed",
            "rawArgs": 12345,  # unexpected type
        }
        # Should not crash
        result = cursor_chronicle.format_tool_call(tool_data, 1)
        self.assertIn("some_tool", result)

    def test_unexpected_result_type(self):
        """Test tool call when result is an unexpected type (e.g., int)."""
        tool_data = {
            "tool": 5,
            "name": "some_tool",
            "status": "completed",
            "result": 99999,  # unexpected type
        }
        # Should not crash
        result = cursor_chronicle.format_tool_call(tool_data, 1)
        self.assertIn("some_tool", result)


class TestFormatTokenInfo(unittest.TestCase):
    """Test format_token_info function."""

    def test_format_token_info_empty(self):
        """Test with empty message."""
        result = cursor_chronicle.format_token_info({})
        self.assertEqual(result, "")

    def test_format_token_info_with_tokens(self):
        """Test with token count."""
        message = {"token_count": {"inputTokens": 100, "outputTokens": 50}}
        result = cursor_chronicle.format_token_info(message)
        self.assertIn("Tokens:", result)
        self.assertIn("100→50", result)
        self.assertIn("150 total", result)

    def test_format_token_info_agentic(self):
        """Test with agentic mode."""
        message = {"is_agentic": True}
        result = cursor_chronicle.format_token_info(message)
        self.assertIn("Agentic mode: enabled", result)

    def test_format_token_info_unified_mode(self):
        """Test with unified mode."""
        message = {"unified_mode": 4}
        result = cursor_chronicle.format_token_info(message)
        self.assertIn("Unified mode: 4", result)

    def test_format_token_info_web_search(self):
        """Test with web search."""
        message = {"use_web": True}
        result = cursor_chronicle.format_token_info(message)
        self.assertIn("Web search: used", result)

    def test_format_token_info_capabilities(self):
        """Test with capabilities."""
        message = {"capabilities_ran": {"cap1": True, "cap2": True, "cap3": True, "cap4": True}}
        result = cursor_chronicle.format_token_info(message)
        self.assertIn("Capabilities:", result)
        self.assertIn("and 1 more", result)

    def test_format_token_info_refunded(self):
        """Test with refunded status."""
        message = {"is_refunded": True}
        result = cursor_chronicle.format_token_info(message)
        self.assertIn("refunded", result)

    def test_format_token_info_usage_uuid(self):
        """Test with usage UUID."""
        message = {"usage_uuid": "12345678-abcd-efgh-ijkl-mnopqrstuvwx"}
        result = cursor_chronicle.format_token_info(message)
        self.assertIn("Usage ID: 12345678", result)


class TestInferModelFromContext(unittest.TestCase):
    """Test infer_model_from_context function."""

    def test_infer_claude_from_text(self):
        """Test inferring Claude from text mention."""
        message = {"text": "Using Claude Sonnet for this task"}
        result = cursor_chronicle.infer_model_from_context(message, 1000)
        self.assertIn("Claude", result)

    def test_infer_gpt_from_text(self):
        """Test inferring GPT from text mention."""
        message = {"text": "Using GPT-4 for this task"}
        result = cursor_chronicle.infer_model_from_context(message, 1000)
        self.assertIn("GPT", result)

    def test_infer_o1_from_text(self):
        """Test inferring o1 from text mention."""
        message = {"text": "Using o1 model"}
        result = cursor_chronicle.infer_model_from_context(message, 1000)
        self.assertIn("o1", result)

    def test_infer_from_agentic(self):
        """Test inferring from agentic mode."""
        message = {"text": "Hello world", "is_agentic": True, "token_count": {"inputTokens": 100, "outputTokens": 200}}
        result = cursor_chronicle.infer_model_from_context(message, 300)
        self.assertIn("Claude", result)
        self.assertIn("agentic", result)

    def test_infer_from_high_tokens(self):
        """Test inferring from high token usage."""
        message = {"text": "Hello world", "is_agentic": False, "token_count": {"inputTokens": 50000, "outputTokens": 60000}}
        result = cursor_chronicle.infer_model_from_context(message, 110000)
        self.assertIn("Claude", result)
        self.assertIn("high token", result)

    def test_infer_from_unified_mode_4(self):
        """Test inferring from unified mode 4."""
        message = {"text": "", "is_agentic": False, "unified_mode": 4}
        result = cursor_chronicle.infer_model_from_context(message, 1000)
        self.assertIn("Advanced model", result)

    def test_infer_from_unified_mode_2(self):
        """Test inferring from unified mode 2."""
        message = {"text": "", "is_agentic": False, "unified_mode": 2}
        result = cursor_chronicle.infer_model_from_context(message, 1000)
        self.assertIn("Standard model", result)

    def test_infer_from_many_capabilities(self):
        """Test inferring from many capabilities."""
        message = {"text": "", "is_agentic": False, "capabilities_ran": {f"cap{i}": True for i in range(10)}}
        result = cursor_chronicle.infer_model_from_context(message, 1000)
        self.assertIn("complex capabilities", result)

    def test_infer_cannot_infer(self):
        """Test when cannot infer model."""
        message = {"text": "Hello", "is_agentic": False}
        result = cursor_chronicle.infer_model_from_context(message, 100)
        self.assertEqual(result, "")


class TestFormatDialog(unittest.TestCase):
    """Test format_dialog function."""

    def test_format_dialog_basic(self):
        """Test basic dialog formatting."""
        messages = [
            {"type": 1, "text": "Hello", "attached_files": [], "is_thought": False},
            {"type": 2, "text": "Hi there!", "tool_data": None, "attached_files": [], "is_thought": False},
        ]
        result = cursor_chronicle.format_dialog(messages, "Test Dialog", "TestProject", 1)
        self.assertIn("TestProject", result)
        self.assertIn("Test Dialog", result)
        self.assertIn("USER", result)
        self.assertIn("AI", result)

    def test_format_dialog_with_thinking(self):
        """Test dialog with thinking bubble."""
        messages = [
            {"type": 2, "text": "", "is_thought": True, "thinking_duration": 5000, "thinking_content": "Analyzing the problem...", "attached_files": []}
        ]
        result = cursor_chronicle.format_dialog(messages, "Test", "Project", 1)
        self.assertIn("THINKING", result)
        self.assertIn("5.0s", result)
        self.assertIn("Analyzing", result)

    def test_format_dialog_with_long_thinking_content(self):
        """Test dialog with long thinking content (truncated)."""
        long_content = "x" * 1000
        messages = [
            {"type": 2, "text": "", "is_thought": True, "thinking_duration": 1000, "thinking_content": long_content, "attached_files": []}
        ]
        result = cursor_chronicle.format_dialog(messages, "Test", "Project", 1)
        self.assertIn("...", result)

    def test_format_dialog_with_attached_files(self):
        """Test dialog with attached files."""
        messages = [
            {"type": 1, "text": "Check this file", "attached_files": [{"type": "active", "path": "/test.py"}], "is_thought": False}
        ]
        result = cursor_chronicle.format_dialog(messages, "Test", "Project", 1)
        self.assertIn("ATTACHED FILES", result)

    def test_format_dialog_with_tool_call(self):
        """Test dialog with tool call."""
        messages = [
            {"type": 2, "text": "Done", "tool_data": {"tool": 5, "name": "read_file", "status": "done"}, "attached_files": [], "is_thought": False}
        ]
        result = cursor_chronicle.format_dialog(messages, "Test", "Project", 1)
        self.assertIn("TOOL", result)

    def test_format_dialog_other_type(self):
        """Test dialog with other message type."""
        messages = [
            {"type": 99, "text": "Some message", "tool_data": None, "attached_files": [], "is_thought": False}
        ]
        result = cursor_chronicle.format_dialog(messages, "Test", "Project", 1)
        self.assertIn("MESSAGE (type 99)", result)

    def test_format_dialog_other_type_with_tool(self):
        """Test dialog with other type and tool."""
        messages = [
            {"type": 99, "text": "", "tool_data": {"tool": 5, "name": "test", "status": "done"}, "attached_files": [], "is_thought": False}
        ]
        result = cursor_chronicle.format_dialog(messages, "Test", "Project", 1)
        self.assertIn("MESSAGE (type 99)", result)
        self.assertIn("TOOL", result)


if __name__ == "__main__":
    unittest.main()
