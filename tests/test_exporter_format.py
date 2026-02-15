"""
Tests for exporter.py module - Message and dialog formatting functions.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cursor_chronicle.config import VERBOSITY_COMPACT, VERBOSITY_FULL, VERBOSITY_STANDARD
from cursor_chronicle.exporter import format_dialog_md, format_message_md, show_export_summary


class TestFormatMessageMd(unittest.TestCase):
    """Test format_message_md function."""

    def test_user_message_compact(self):
        """Test user message at compact verbosity."""
        msg = {
            "type": 1,
            "text": "Hello, how are you?",
            "attached_files": [{"type": "active", "path": "/test.py"}],
            "is_thought": False,
        }
        result = format_message_md(msg, VERBOSITY_COMPACT)
        self.assertIn("### 👤 User", result)
        self.assertIn("Hello, how are you?", result)
        # Compact should not include attached files
        self.assertNotIn("Attached Files", result)

    def test_user_message_standard(self):
        """Test user message at standard verbosity."""
        msg = {
            "type": 1,
            "text": "Check this file",
            "attached_files": [{"type": "active", "path": "/test.py"}],
            "is_thought": False,
        }
        result = format_message_md(msg, VERBOSITY_STANDARD)
        self.assertIn("### 👤 User", result)
        self.assertIn("Attached Files", result)

    def test_ai_message(self):
        """Test AI response message."""
        msg = {
            "type": 2,
            "text": "Here is the answer.",
            "tool_data": None,
            "attached_files": [],
            "is_thought": False,
            "token_count": {"inputTokens": 100, "outputTokens": 50},
        }
        result = format_message_md(msg, VERBOSITY_STANDARD)
        self.assertIn("### 🤖 Assistant", result)
        self.assertIn("Here is the answer.", result)
        self.assertIn("Tokens", result)

    def test_thinking_message_compact(self):
        """Test thinking message at compact verbosity (skipped)."""
        msg = {
            "type": 2,
            "text": "",
            "is_thought": True,
            "thinking_duration": 5000,
            "thinking_content": "Analyzing...",
            "attached_files": [],
        }
        result = format_message_md(msg, VERBOSITY_COMPACT)
        self.assertEqual(result, "")

    def test_thinking_message_standard(self):
        """Test thinking message at standard verbosity."""
        msg = {
            "type": 2,
            "text": "",
            "is_thought": True,
            "thinking_duration": 5000,
            "thinking_content": "Analyzing the problem...",
            "attached_files": [],
        }
        result = format_message_md(msg, VERBOSITY_STANDARD)
        self.assertIn("AI Thinking", result)
        self.assertIn("5.0s", result)

    def test_thinking_message_full(self):
        """Test thinking message at full verbosity (no truncation)."""
        long_content = "x" * 1000
        msg = {
            "type": 2,
            "text": "",
            "is_thought": True,
            "thinking_duration": 2000,
            "thinking_content": long_content,
            "attached_files": [],
        }
        result = format_message_md(msg, VERBOSITY_FULL)
        self.assertIn(long_content, result)
        self.assertNotIn("...", result)

    def test_tool_call_compact(self):
        """Test tool call at compact verbosity."""
        msg = {
            "type": 2,
            "text": "",
            "tool_data": {"tool": 5, "name": "read_file", "status": "completed"},
            "attached_files": [],
            "is_thought": False,
        }
        result = format_message_md(msg, VERBOSITY_COMPACT)
        self.assertIn("read_file", result)
        # Compact should be a single-line blockquote
        self.assertIn("> 🛠️", result)

    def test_tool_call_standard(self):
        """Test tool call at standard verbosity."""
        msg = {
            "type": 2,
            "text": "",
            "tool_data": {
                "tool": 5,
                "name": "read_file",
                "status": "completed",
                "userDecision": "accepted",
                "rawArgs": '{"path": "/test.py"}',
            },
            "attached_files": [],
            "is_thought": False,
        }
        result = format_message_md(msg, VERBOSITY_STANDARD)
        self.assertIn("#### 🛠️ Tool", result)
        self.assertIn("read_file", result)
        self.assertIn("Parameters", result)
        self.assertIn("/test.py", result)

    def test_tool_call_standard_dict_rawargs(self):
        """Test tool call when rawArgs is already a dict (not JSON string)."""
        msg = {
            "type": 2,
            "text": "",
            "tool_data": {
                "tool": 5,
                "name": "read_file",
                "status": "completed",
                "userDecision": "accepted",
                "rawArgs": {"path": "/test.py"},  # dict, not JSON string
            },
            "attached_files": [],
            "is_thought": False,
        }
        result = format_message_md(msg, VERBOSITY_STANDARD)
        self.assertIn("#### 🛠️ Tool", result)
        self.assertIn("read_file", result)
        self.assertIn("Parameters", result)
        self.assertIn("/test.py", result)

    def test_tool_call_full_dict_result(self):
        """Test tool call at full verbosity when result is already a dict."""
        msg = {
            "type": 2,
            "text": "",
            "tool_data": {
                "tool": 5,
                "name": "read_file",
                "status": "completed",
                "rawArgs": {"path": "/test.py"},  # dict
                "result": {"contents": "file content here"},  # dict, not JSON string
            },
            "attached_files": [],
            "is_thought": False,
        }
        result = format_message_md(msg, VERBOSITY_FULL)
        self.assertIn("Result", result)
        self.assertIn("file content here", result)

    def test_tool_call_full_list_result(self):
        """Test tool call at full verbosity when result is a list."""
        msg = {
            "type": 2,
            "text": "",
            "tool_data": {
                "tool": 5,
                "name": "some_tool",
                "status": "completed",
                "rawArgs": '{"query": "test"}',
                "result": [{"file": "a.py"}, {"file": "b.py"}],  # list, not JSON string
            },
            "attached_files": [],
            "is_thought": False,
        }
        result = format_message_md(msg, VERBOSITY_FULL)
        self.assertIn("Result", result)
        self.assertIn("a.py", result)

    def test_tool_call_rawargs_unexpected_type(self):
        """Test tool call when rawArgs is an unexpected type (e.g., int)."""
        msg = {
            "type": 2,
            "text": "",
            "tool_data": {
                "tool": 5,
                "name": "some_tool",
                "status": "completed",
                "rawArgs": 12345,  # unexpected type
            },
            "attached_files": [],
            "is_thought": False,
        }
        # Should not crash
        result = format_message_md(msg, VERBOSITY_STANDARD)
        self.assertIn("some_tool", result)

    def test_empty_message(self):
        """Test empty message returns empty string."""
        msg = {
            "type": 1,
            "text": "",
            "tool_data": None,
            "attached_files": [],
            "is_thought": False,
        }
        result = format_message_md(msg, VERBOSITY_STANDARD)
        self.assertEqual(result, "")

    def test_other_message_type(self):
        """Test message with unknown type."""
        msg = {
            "type": 99,
            "text": "Some text",
            "tool_data": None,
            "attached_files": [],
            "is_thought": False,
        }
        result = format_message_md(msg, VERBOSITY_STANDARD)
        self.assertIn("Message (type 99)", result)
        self.assertIn("Some text", result)


class TestFormatDialogMd(unittest.TestCase):
    """Test format_dialog_md function."""

    def test_basic_dialog(self):
        """Test formatting a basic dialog."""
        messages = [
            {
                "type": 1, "text": "Hello", "attached_files": [],
                "is_thought": False, "tool_data": None,
            },
            {
                "type": 2, "text": "Hi there!", "attached_files": [],
                "is_thought": False, "tool_data": None,
                "token_count": {},
            },
        ]
        result = format_dialog_md(
            messages, "Test Dialog", "TestProject",
            created_at=1749736260000, last_updated=1749736300000,
            verbosity=VERBOSITY_STANDARD,
        )
        self.assertIn("# Test Dialog", result)
        self.assertIn("**Project:** TestProject", result)
        self.assertIn("**Created:**", result)
        self.assertIn("**Last Updated:**", result)
        self.assertIn("**Messages:** 2", result)
        self.assertIn("Hello", result)
        self.assertIn("Hi there!", result)

    def test_dialog_with_zero_timestamps(self):
        """Test dialog with zero timestamps."""
        messages = [
            {
                "type": 1, "text": "Test", "attached_files": [],
                "is_thought": False, "tool_data": None,
            },
        ]
        result = format_dialog_md(
            messages, "Test", "Project",
            created_at=0, last_updated=0,
            verbosity=VERBOSITY_STANDARD,
        )
        self.assertIn("# Test", result)
        self.assertNotIn("**Created:**", result)

    def test_dialog_separators(self):
        """Test that messages are separated by horizontal rules."""
        messages = [
            {
                "type": 1, "text": "Hello", "attached_files": [],
                "is_thought": False, "tool_data": None,
            },
            {
                "type": 2, "text": "World", "attached_files": [],
                "is_thought": False, "tool_data": None,
                "token_count": {},
            },
        ]
        result = format_dialog_md(
            messages, "Test", "Project",
            created_at=1749736260000, last_updated=1749736260000,
            verbosity=VERBOSITY_COMPACT,
        )
        self.assertGreater(result.count("---"), 1)


class TestShowExportSummary(unittest.TestCase):
    """Test show_export_summary function."""

    def test_basic_summary(self):
        """Test basic export summary."""
        stats = {
            "total_dialogs": 10,
            "exported": 8,
            "errors": 1,
            "skipped": 1,
            "export_path": "/tmp/test",
            "verbosity": 2,
        }
        result = show_export_summary(stats)
        self.assertIn("EXPORT SUMMARY", result)
        self.assertIn("Total dialogs: 10", result)
        self.assertIn("Exported:    8", result)
        self.assertIn("Errors:      1", result)
        self.assertIn("Skipped:     1", result)
        self.assertIn("standard", result)

    def test_summary_no_errors(self):
        """Test summary with no errors or skips."""
        stats = {
            "total_dialogs": 5,
            "exported": 5,
            "errors": 0,
            "skipped": 0,
            "export_path": "/tmp/test",
            "verbosity": 1,
        }
        result = show_export_summary(stats)
        self.assertNotIn("Errors", result)
        self.assertNotIn("Skipped", result)
        self.assertIn("compact", result)

    def test_summary_full_verbosity(self):
        """Test summary with full verbosity label."""
        stats = {
            "total_dialogs": 1,
            "exported": 1,
            "errors": 0,
            "skipped": 0,
            "export_path": "/tmp/test",
            "verbosity": 3,
        }
        result = show_export_summary(stats)
        self.assertIn("full", result)


if __name__ == "__main__":
    unittest.main()
