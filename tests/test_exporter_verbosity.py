"""
Tests for exporter.py module - Verbosity levels and progress callback.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from cursor_chronicle.config import VERBOSITY_COMPACT, VERBOSITY_FULL, VERBOSITY_STANDARD
from cursor_chronicle.exporter import export_dialogs, format_dialog_md, format_message_md


class TestVerbosityLevels(unittest.TestCase):
    """Test that different verbosity levels produce different output."""

    def _make_messages(self):
        """Create test messages with various content."""
        return [
            {
                "type": 1,
                "text": "User message",
                "attached_files": [{"type": "active", "path": "/test.py"}],
                "is_thought": False,
                "tool_data": None,
            },
            {
                "type": 2,
                "text": "",
                "is_thought": True,
                "thinking_duration": 3000,
                "thinking_content": "Thinking deeply about this...",
                "attached_files": [],
            },
            {
                "type": 2,
                "text": "",
                "tool_data": {
                    "tool": 5,
                    "name": "read_file",
                    "status": "completed",
                    "rawArgs": '{"path": "/test.py"}',
                    "result": '{"contents": "file content here"}',
                },
                "attached_files": [],
                "is_thought": False,
            },
            {
                "type": 2,
                "text": "",
                "tool_data": {
                    "tool": 5,
                    "name": "grep",
                    "status": "completed",
                    "rawArgs": {"pattern": "TODO", "path": "/src"},  # dict, not string
                    "result": {"matches": ["line1", "line2"]},  # dict, not string
                },
                "attached_files": [],
                "is_thought": False,
            },
            {
                "type": 2,
                "text": "Here is my response.",
                "tool_data": None,
                "attached_files": [],
                "is_thought": False,
                "token_count": {"inputTokens": 500, "outputTokens": 200},
            },
        ]

    def test_compact_is_shortest(self):
        """Test that compact produces less output than standard."""
        messages = self._make_messages()
        compact = format_dialog_md(messages, "Test", "P", 1000000, 1000000, VERBOSITY_COMPACT)
        standard = format_dialog_md(messages, "Test", "P", 1000000, 1000000, VERBOSITY_STANDARD)
        self.assertLess(len(compact), len(standard))

    def test_full_is_longest(self):
        """Test that full produces more output than standard."""
        messages = self._make_messages()
        standard = format_dialog_md(messages, "Test", "P", 1000000, 1000000, VERBOSITY_STANDARD)
        full = format_dialog_md(messages, "Test", "P", 1000000, 1000000, VERBOSITY_FULL)
        self.assertLessEqual(len(standard), len(full))

    def test_compact_no_thinking(self):
        """Test that compact doesn't include thinking content."""
        messages = self._make_messages()
        result = format_dialog_md(messages, "Test", "P", 1000000, 1000000, VERBOSITY_COMPACT)
        self.assertNotIn("Thinking", result)

    def test_full_includes_tool_results(self):
        """Test that full includes tool results."""
        messages = self._make_messages()
        result = format_dialog_md(messages, "Test", "P", 1000000, 1000000, VERBOSITY_FULL)
        self.assertIn("Result", result)
        self.assertIn("file content here", result)

    def test_standard_no_tool_results(self):
        """Test that standard verbosity does NOT include tool results."""
        messages = self._make_messages()
        result = format_dialog_md(messages, "Test", "P", 1000000, 1000000, VERBOSITY_STANDARD)
        self.assertNotIn("file content here", result)

    def test_compact_no_parameters(self):
        """Test that compact verbosity does NOT include tool parameters."""
        messages = self._make_messages()
        result = format_dialog_md(messages, "Test", "P", 1000000, 1000000, VERBOSITY_COMPACT)
        self.assertNotIn("Parameters", result)

    def test_standard_includes_parameters(self):
        """Test that standard verbosity includes tool parameters."""
        messages = self._make_messages()
        result = format_dialog_md(messages, "Test", "P", 1000000, 1000000, VERBOSITY_STANDARD)
        self.assertIn("Parameters", result)

    def test_compact_no_token_info(self):
        """Test that compact verbosity does NOT include token info."""
        messages = self._make_messages()
        result = format_dialog_md(messages, "Test", "P", 1000000, 1000000, VERBOSITY_COMPACT)
        self.assertNotIn("Tokens", result)

    def test_standard_includes_token_info(self):
        """Test that standard verbosity includes token info."""
        messages = self._make_messages()
        result = format_dialog_md(messages, "Test", "P", 1000000, 1000000, VERBOSITY_STANDARD)
        self.assertIn("Tokens", result)


class TestFullVerbosityNoTruncation(unittest.TestCase):
    """Test that VERBOSITY_FULL does not truncate tool results or file content."""

    def test_full_no_truncation_tool_result(self):
        """Test that full verbosity does NOT truncate large tool results."""
        large_content = "x" * 5000
        msg = {
            "type": 2,
            "text": "",
            "tool_data": {
                "tool": 5,
                "name": "read_file",
                "status": "completed",
                "rawArgs": '{"path": "/big.py"}',
                "result": json.dumps({"contents": large_content}),
            },
            "attached_files": [],
            "is_thought": False,
        }
        result = format_message_md(msg, VERBOSITY_FULL)
        self.assertIn(large_content, result)
        self.assertNotIn("(truncated)", result)

    def test_full_no_truncation_parameters(self):
        """Test that full verbosity does NOT truncate long parameters."""
        long_param = "y" * 500
        msg = {
            "type": 2,
            "text": "",
            "tool_data": {
                "tool": 5,
                "name": "read_file",
                "status": "completed",
                "rawArgs": json.dumps({"path": long_param}),
            },
            "attached_files": [],
            "is_thought": False,
        }
        result = format_message_md(msg, VERBOSITY_FULL)
        self.assertIn(long_param, result)
        self.assertNotIn("...", result)

    def test_standard_truncates_long_parameters(self):
        """Test that standard verbosity DOES truncate long parameters."""
        long_param = "z" * 500
        msg = {
            "type": 2,
            "text": "",
            "tool_data": {
                "tool": 5,
                "name": "read_file",
                "status": "completed",
                "rawArgs": json.dumps({"path": long_param}),
            },
            "attached_files": [],
            "is_thought": False,
        }
        result = format_message_md(msg, VERBOSITY_STANDARD)
        self.assertNotIn(long_param, result)
        self.assertIn("...", result)

    def test_full_no_truncation_file_content(self):
        """Test that full verbosity does NOT truncate attached file content."""
        large_file_content = "line " * 500
        msg = {
            "type": 1,
            "text": "Check this",
            "attached_files": [{
                "type": "context",
                "path": "/big_file.py",
                "content": large_file_content,
            }],
            "is_thought": False,
        }
        result = format_message_md(msg, VERBOSITY_FULL)
        self.assertIn(large_file_content, result)
        self.assertNotIn("...", result)

    def test_full_thinking_not_truncated(self):
        """Test that full verbosity does NOT truncate thinking content."""
        long_thinking = "thought " * 200
        msg = {
            "type": 2,
            "text": "",
            "is_thought": True,
            "thinking_duration": 5000,
            "thinking_content": long_thinking,
            "attached_files": [],
        }
        result = format_message_md(msg, VERBOSITY_FULL)
        self.assertIn(long_thinking, result)
        self.assertNotIn("...", result)

    def test_standard_truncates_thinking(self):
        """Test that standard verbosity DOES truncate long thinking content."""
        long_thinking = "thought " * 200
        msg = {
            "type": 2,
            "text": "",
            "is_thought": True,
            "thinking_duration": 5000,
            "thinking_content": long_thinking,
            "attached_files": [],
        }
        result = format_message_md(msg, VERBOSITY_STANDARD)
        self.assertIn("...", result)
        self.assertNotIn(long_thinking, result)


class TestProgressCallback(unittest.TestCase):
    """Test that export_dialogs calls the progress callback correctly."""

    def _make_viewer_mock(self, dialogs):
        viewer = MagicMock()
        viewer.get_all_dialogs.return_value = dialogs
        return viewer

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_callback_called_for_each_dialog(self, mock_get_messages, mock_load_config):
        """Test that progress callback is called once per dialog."""
        mock_load_config.return_value = {"export_path": "/tmp", "verbosity": 2}
        mock_get_messages.return_value = [
            {"type": 1, "text": "Hi", "attached_files": [], "is_thought": False, "tool_data": None},
        ]

        dialogs = [
            {"composer_id": f"id{i}", "name": f"D{i}", "project_name": "P",
             "created_at": 1749736260000 + i * 1000, "last_updated": 1749736260000}
            for i in range(5)
        ]

        callback = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            viewer = self._make_viewer_mock(dialogs)
            export_dialogs(viewer, export_path=Path(tmpdir), verbosity=2, progress_callback=callback)

        self.assertEqual(callback.call_count, 5)

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_callback_receives_correct_percent(self, mock_get_messages, mock_load_config):
        """Test that progress callback receives correct percentage."""
        mock_load_config.return_value = {"export_path": "/tmp", "verbosity": 2}
        mock_get_messages.return_value = [
            {"type": 1, "text": "Hi", "attached_files": [], "is_thought": False, "tool_data": None},
        ]

        dialogs = [
            {"composer_id": "id1", "name": "D1", "project_name": "P",
             "created_at": 1749736260000, "last_updated": 1749736260000},
            {"composer_id": "id2", "name": "D2", "project_name": "P",
             "created_at": 1749736261000, "last_updated": 1749736261000},
        ]

        received = []
        def capture(info):
            received.append(info.copy())

        with tempfile.TemporaryDirectory() as tmpdir:
            viewer = self._make_viewer_mock(dialogs)
            export_dialogs(viewer, export_path=Path(tmpdir), verbosity=2, progress_callback=capture)

        self.assertEqual(received[0]["percent"], 50)
        self.assertEqual(received[0]["current"], 1)
        self.assertEqual(received[1]["percent"], 100)
        self.assertEqual(received[1]["current"], 2)

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_callback_reports_skipped(self, mock_get_messages, mock_load_config):
        """Test that progress callback reports skipped dialogs."""
        mock_load_config.return_value = {"export_path": "/tmp", "verbosity": 2}
        mock_get_messages.return_value = []  # empty = skipped

        dialogs = [
            {"composer_id": "id1", "name": "Empty", "project_name": "P",
             "created_at": 1749736260000, "last_updated": 1749736260000},
        ]

        received = []
        def capture(info):
            received.append(info.copy())

        with tempfile.TemporaryDirectory() as tmpdir:
            viewer = self._make_viewer_mock(dialogs)
            export_dialogs(viewer, export_path=Path(tmpdir), verbosity=2, progress_callback=capture)

        self.assertEqual(received[0]["status"], "skipped")

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_callback_reports_error(self, mock_get_messages, mock_load_config):
        """Test that progress callback reports errors."""
        mock_load_config.return_value = {"export_path": "/tmp", "verbosity": 2}
        mock_get_messages.side_effect = Exception("DB error")

        dialogs = [
            {"composer_id": "id1", "name": "Bad", "project_name": "P",
             "created_at": 1749736260000, "last_updated": 1749736260000},
        ]

        received = []
        def capture(info):
            received.append(info.copy())

        with tempfile.TemporaryDirectory() as tmpdir:
            viewer = self._make_viewer_mock(dialogs)
            export_dialogs(viewer, export_path=Path(tmpdir), verbosity=2, progress_callback=capture)

        self.assertEqual(received[0]["status"], "error")

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_no_callback_no_error(self, mock_get_messages, mock_load_config):
        """Test that export works fine without a progress callback."""
        mock_load_config.return_value = {"export_path": "/tmp", "verbosity": 2}
        mock_get_messages.return_value = [
            {"type": 1, "text": "Hi", "attached_files": [], "is_thought": False, "tool_data": None},
        ]

        dialogs = [
            {"composer_id": "id1", "name": "D1", "project_name": "P",
             "created_at": 1749736260000, "last_updated": 1749736260000},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            viewer = self._make_viewer_mock(dialogs)
            stats = export_dialogs(viewer, export_path=Path(tmpdir), verbosity=2)

        self.assertEqual(stats["exported"], 1)


if __name__ == "__main__":
    unittest.main()
