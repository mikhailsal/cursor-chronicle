"""Tests for formatters.py module - output formatting functions."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cursor_chronicle


class TestFormatAttachedFiles(unittest.TestCase):
    """Test format_attached_files function."""

    def test_empty(self):
        self.assertEqual(cursor_chronicle.format_attached_files([], 1), "")

    def test_basic(self):
        files = [
            {"type": "active", "path": "src/main.py", "line": 42},
            {"type": "selected", "path": "src/utils.py"},
        ]
        result = cursor_chronicle.format_attached_files(files, 1)
        self.assertIn("Active file: src/main.py", result)
        self.assertIn("Selected file: src/utils.py", result)
        self.assertIn("Line: 42", result)

    def test_with_preview(self):
        files = [{"type": "active", "path": "/test.py", "preview": "def function(): pass"}]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("Preview:", result)
        self.assertIn("def function():", result)

    def test_long_preview_truncated(self):
        files = [{"type": "active", "path": "/test.py", "preview": "x" * 200}]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("...", result)

    def test_selected_with_selection(self):
        files = [{"type": "selected", "path": "/test.py", "selection": "1-10"}]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("Selection: 1-10", result)

    def test_context_with_content(self):
        files = [{"type": "context", "path": "/test.py", "line_range": "10-20", "content": "def test():"}]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("Lines: 10-20", result)
        self.assertIn("Content:", result)

    def test_context_long_content_truncated(self):
        files = [{"type": "context", "path": "/test.py", "content": "x" * 300}]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("...", result)

    def test_many_project_files(self):
        files = [{"type": "project", "path": f"/file{i}.py"} for i in range(20)]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("20 files", result)
        self.assertIn("and 10 more files", result)

    def test_selected_context(self):
        files = [{"type": "selected_context", "path": "/test.py", "selection": "5-15"}]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("Selected in context:", result)
        self.assertIn("Selection: 5-15", result)

    def test_missing_path(self):
        files = [{"type": "active"}]
        result = cursor_chronicle.format_attached_files(files, 10)
        self.assertIn("unknown", result)


class TestFormatToolCall(unittest.TestCase):
    """Test format_tool_call function."""

    def test_empty_and_null(self):
        self.assertEqual(cursor_chronicle.format_tool_call({}, 1), "")
        self.assertEqual(cursor_chronicle.format_tool_call({"tool": None}, 1), "")

    def test_basic(self):
        tool_data = {"tool": 5, "name": "read_file", "status": "completed", "userDecision": "accepted"}
        result = cursor_chronicle.format_tool_call(tool_data, 1)
        self.assertIn("TOOL", result)
        self.assertIn("Read File", result)
        self.assertIn("read_file", result)
        self.assertIn("completed", result)
        self.assertIn("✅", result)

    def test_rejected(self):
        tool_data = {"tool": 7, "name": "edit_file", "status": "completed", "userDecision": "rejected"}
        self.assertIn("❌", cursor_chronicle.format_tool_call(tool_data, 1))

    def test_unknown_tool_type(self):
        tool_data = {"tool": 999, "name": "unknown_tool", "status": "completed"}
        self.assertIn("Tool 999", cursor_chronicle.format_tool_call(tool_data, 1))

    def test_with_raw_args(self):
        tool_data = {"tool": 5, "name": "read_file", "status": "completed",
                     "rawArgs": json.dumps({"path": "/path/to/file.py"})}
        result = cursor_chronicle.format_tool_call(tool_data, 1)
        self.assertIn("path", result)
        self.assertIn("/path/to/file.py", result)

    def test_explanation_not_truncated(self):
        long_explanation = "x" * 200
        tool_data = {"tool": 5, "name": "read_file", "status": "completed",
                     "rawArgs": json.dumps({"explanation": long_explanation})}
        self.assertIn(long_explanation, cursor_chronicle.format_tool_call(tool_data, 1))

    def test_code_edit_truncation(self):
        code_edit = "\n".join([f"line {i}" for i in range(100)])
        tool_data = {"tool": 7, "name": "edit_file", "status": "completed",
                     "rawArgs": json.dumps({"code_edit": code_edit})}
        self.assertIn("more lines", cursor_chronicle.format_tool_call(tool_data, 5))

    def test_long_param_truncation(self):
        tool_data = {"tool": 5, "name": "read_file", "status": "completed",
                     "rawArgs": json.dumps({"path": "x" * 200})}
        self.assertIn("...", cursor_chronicle.format_tool_call(tool_data, 1))

    def test_read_file_result(self):
        contents = "\n".join([f"line {i}" for i in range(100)])
        tool_data = {"tool": 5, "name": "read_file", "status": "completed",
                     "result": json.dumps({"contents": contents, "file": "/test.py"})}
        result = cursor_chronicle.format_tool_call(tool_data, 5)
        self.assertIn("more lines", result)
        self.assertIn("file", result)

    def test_terminal_cmd_result(self):
        output = "\n".join([f"output line {i}" for i in range(100)])
        tool_data = {"tool": 15, "name": "run_terminal_cmd", "status": "completed",
                     "result": json.dumps({"output": output, "exitCodeV2": 0})}
        result = cursor_chronicle.format_tool_call(tool_data, 5)
        self.assertIn("Exit code: 0", result)
        self.assertIn("more lines", result)

    def test_edit_file_diff_result(self):
        tool_data = {"tool": 7, "name": "edit_file", "status": "completed",
                     "result": json.dumps({"diff": {"chunks": [{"linesAdded": 5, "linesRemoved": 3, "diffString": "+new\n-old"}]}})}
        result1 = cursor_chronicle.format_tool_call(tool_data, 1)
        self.assertIn("+5 -3", result1)
        self.assertIn("details hidden", result1)
        result2 = cursor_chronicle.format_tool_call(tool_data, 10)
        self.assertIn("+new", result2)


class TestFormatToolCallDictTypes(unittest.TestCase):
    """Test format_tool_call with dict-typed rawArgs and result."""

    def test_dict_raw_args(self):
        tool_data = {"tool": 5, "name": "read_file", "status": "completed",
                     "rawArgs": {"path": "/path/to/file.py"}}
        result = cursor_chronicle.format_tool_call(tool_data, 1)
        self.assertIn("path", result)
        self.assertIn("/path/to/file.py", result)

    def test_dict_result(self):
        tool_data = {"tool": 5, "name": "read_file", "status": "completed",
                     "result": {"contents": "hello world", "file": "/test.py"}}
        result = cursor_chronicle.format_tool_call(tool_data, 5)
        self.assertIn("Result", result)
        self.assertIn("hello world", result)

    def test_list_result(self):
        tool_data = {"tool": 5, "name": "some_tool", "status": "completed",
                     "result": [{"file": "a.py"}, {"file": "b.py"}]}
        self.assertIn("Result", cursor_chronicle.format_tool_call(tool_data, 5))

    def test_unexpected_types_no_crash(self):
        # rawArgs as int
        tool_data = {"tool": 5, "name": "some_tool", "status": "completed", "rawArgs": 12345}
        self.assertIn("some_tool", cursor_chronicle.format_tool_call(tool_data, 1))
        # result as int
        tool_data = {"tool": 5, "name": "some_tool", "status": "completed", "result": 99999}
        self.assertIn("some_tool", cursor_chronicle.format_tool_call(tool_data, 1))


class TestFormatTokenInfo(unittest.TestCase):
    """Test format_token_info function."""

    def test_empty(self):
        self.assertEqual(cursor_chronicle.format_token_info({}), "")

    def test_with_tokens(self):
        result = cursor_chronicle.format_token_info({"token_count": {"inputTokens": 100, "outputTokens": 50}})
        self.assertIn("Tokens:", result)
        self.assertIn("100→50", result)
        self.assertIn("150 total", result)

    def test_agentic(self):
        self.assertIn("Agentic mode: enabled", cursor_chronicle.format_token_info({"is_agentic": True}))

    def test_unified_mode(self):
        self.assertIn("Unified mode: 4", cursor_chronicle.format_token_info({"unified_mode": 4}))

    def test_web_search(self):
        self.assertIn("Web search: used", cursor_chronicle.format_token_info({"use_web": True}))

    def test_capabilities(self):
        result = cursor_chronicle.format_token_info({"capabilities_ran": {"cap1": True, "cap2": True, "cap3": True, "cap4": True}})
        self.assertIn("Capabilities:", result)
        self.assertIn("and 1 more", result)

    def test_refunded(self):
        self.assertIn("refunded", cursor_chronicle.format_token_info({"is_refunded": True}))

    def test_usage_uuid(self):
        result = cursor_chronicle.format_token_info({"usage_uuid": "12345678-abcd-efgh-ijkl-mnopqrstuvwx"})
        self.assertIn("Usage ID: 12345678", result)


class TestInferModelFromContext(unittest.TestCase):
    """Test infer_model_from_context function."""

    def test_infer_claude_from_text(self):
        self.assertIn("Claude", cursor_chronicle.infer_model_from_context({"text": "Using Claude Sonnet"}, 1000))

    def test_infer_gpt_from_text(self):
        self.assertIn("GPT", cursor_chronicle.infer_model_from_context({"text": "Using GPT-4"}, 1000))

    def test_infer_o1_from_text(self):
        self.assertIn("o1", cursor_chronicle.infer_model_from_context({"text": "Using o1 model"}, 1000))

    def test_infer_from_agentic(self):
        message = {"text": "Hello", "is_agentic": True, "token_count": {"inputTokens": 100, "outputTokens": 200}}
        result = cursor_chronicle.infer_model_from_context(message, 300)
        self.assertIn("Claude", result)
        self.assertIn("agentic", result)

    def test_infer_from_high_tokens(self):
        message = {"text": "Hello", "is_agentic": False, "token_count": {"inputTokens": 50000, "outputTokens": 60000}}
        result = cursor_chronicle.infer_model_from_context(message, 110000)
        self.assertIn("Claude", result)
        self.assertIn("high token", result)

    def test_infer_from_unified_mode(self):
        self.assertIn("Advanced model", cursor_chronicle.infer_model_from_context({"text": "", "is_agentic": False, "unified_mode": 4}, 1000))
        self.assertIn("Standard model", cursor_chronicle.infer_model_from_context({"text": "", "is_agentic": False, "unified_mode": 2}, 1000))

    def test_infer_from_many_capabilities(self):
        message = {"text": "", "is_agentic": False, "capabilities_ran": {f"cap{i}": True for i in range(10)}}
        self.assertIn("complex capabilities", cursor_chronicle.infer_model_from_context(message, 1000))

    def test_cannot_infer(self):
        self.assertEqual("", cursor_chronicle.infer_model_from_context({"text": "Hello", "is_agentic": False}, 100))


class TestFormatDialog(unittest.TestCase):
    """Test format_dialog function."""

    def test_basic(self):
        messages = [
            {"type": 1, "text": "Hello", "attached_files": [], "is_thought": False},
            {"type": 2, "text": "Hi there!", "tool_data": None, "attached_files": [], "is_thought": False},
        ]
        result = cursor_chronicle.format_dialog(messages, "Test Dialog", "TestProject", 1)
        self.assertIn("TestProject", result)
        self.assertIn("Test Dialog", result)
        self.assertIn("USER", result)
        self.assertIn("AI", result)

    def test_with_thinking(self):
        messages = [{"type": 2, "text": "", "is_thought": True, "thinking_duration": 5000, "thinking_content": "Analyzing...", "attached_files": []}]
        result = cursor_chronicle.format_dialog(messages, "Test", "Project", 1)
        self.assertIn("THINKING", result)
        self.assertIn("5.0s", result)
        self.assertIn("Analyzing", result)

    def test_long_thinking_truncated(self):
        messages = [{"type": 2, "text": "", "is_thought": True, "thinking_duration": 1000, "thinking_content": "x" * 1000, "attached_files": []}]
        self.assertIn("...", cursor_chronicle.format_dialog(messages, "Test", "Project", 1))

    def test_with_attached_files(self):
        messages = [{"type": 1, "text": "Check this", "attached_files": [{"type": "active", "path": "/test.py"}], "is_thought": False}]
        self.assertIn("ATTACHED FILES", cursor_chronicle.format_dialog(messages, "Test", "Project", 1))

    def test_with_tool_call(self):
        messages = [{"type": 2, "text": "Done", "tool_data": {"tool": 5, "name": "read_file", "status": "done"}, "attached_files": [], "is_thought": False}]
        self.assertIn("TOOL", cursor_chronicle.format_dialog(messages, "Test", "Project", 1))

    def test_other_type(self):
        messages = [{"type": 99, "text": "Some message", "tool_data": None, "attached_files": [], "is_thought": False}]
        self.assertIn("MESSAGE (type 99)", cursor_chronicle.format_dialog(messages, "Test", "Project", 1))

    def test_other_type_with_tool(self):
        messages = [{"type": 99, "text": "", "tool_data": {"tool": 5, "name": "test", "status": "done"}, "attached_files": [], "is_thought": False}]
        result = cursor_chronicle.format_dialog(messages, "Test", "Project", 1)
        self.assertIn("MESSAGE (type 99)", result)
        self.assertIn("TOOL", result)


if __name__ == "__main__":
    unittest.main()
