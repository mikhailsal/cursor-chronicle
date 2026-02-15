"""
Tests for exporter.py module - Markdown export functionality.
"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from cursor_chronicle.config import VERBOSITY_COMPACT, VERBOSITY_FULL, VERBOSITY_STANDARD
from cursor_chronicle.exporter import (
    build_folder_path,
    build_md_filename,
    export_dialogs,
    format_dialog_md,
    format_message_md,
    sanitize_filename,
    sanitize_project_name,
    show_export_summary,
)


class TestSanitizeFilename(unittest.TestCase):
    """Test sanitize_filename function."""

    def test_basic_name(self):
        """Test basic filename sanitization."""
        result = sanitize_filename("How we should implement logging")
        self.assertEqual(result, "How_we_should_implement_logging")

    def test_special_characters(self):
        """Test removing special characters."""
        result = sanitize_filename('File: "test" <data> |pipe|')
        self.assertEqual(result, "File_test_data_pipe")

    def test_empty_name(self):
        """Test empty name returns Untitled."""
        self.assertEqual(sanitize_filename(""), "Untitled")
        self.assertEqual(sanitize_filename("   "), "Untitled")

    def test_none_name(self):
        """Test None name returns Untitled."""
        self.assertEqual(sanitize_filename(None), "Untitled")

    def test_max_length(self):
        """Test max length truncation."""
        long_name = "A" * 200
        result = sanitize_filename(long_name, max_length=50)
        self.assertLessEqual(len(result), 50)

    def test_multiple_spaces(self):
        """Test multiple spaces collapsed to single underscore."""
        result = sanitize_filename("Hello    World")
        self.assertEqual(result, "Hello_World")

    def test_multiple_underscores(self):
        """Test multiple underscores collapsed."""
        result = sanitize_filename("Hello___World")
        self.assertEqual(result, "Hello_World")

    def test_leading_trailing_stripped(self):
        """Test leading/trailing underscores and dots stripped."""
        result = sanitize_filename("..._test_...")
        self.assertEqual(result, "test")

    def test_all_special_chars(self):
        """Test name with only special characters."""
        result = sanitize_filename(':<>"|?*')
        self.assertEqual(result, "Untitled")


class TestSanitizeProjectName(unittest.TestCase):
    """Test sanitize_project_name function."""

    def test_basic_project(self):
        """Test basic project name."""
        result = sanitize_project_name("my-project")
        self.assertEqual(result, "my-project")

    def test_empty_project(self):
        """Test empty project name."""
        self.assertEqual(sanitize_project_name(""), "Unknown_Project")
        self.assertEqual(sanitize_project_name("   "), "Unknown_Project")

    def test_none_project(self):
        """Test None project name."""
        self.assertEqual(sanitize_project_name(None), "Unknown_Project")

    def test_special_chars_in_project(self):
        """Test special characters in project name."""
        result = sanitize_project_name("my/project:name")
        self.assertEqual(result, "my_project_name")


class TestBuildMdFilename(unittest.TestCase):
    """Test build_md_filename function."""

    def test_basic_filename(self):
        """Test building a basic filename."""
        # 2025-06-12 14:31:00 UTC
        ts = 1749736260000
        result = build_md_filename(ts, "How we should implement logging")
        self.assertTrue(result.endswith(".md"))
        self.assertIn("How_we_should_implement_logging", result)
        # Check date prefix format
        parts = result.split("_", 2)
        self.assertRegex(parts[0], r"\d{4}-\d{2}-\d{2}")

    def test_zero_timestamp(self):
        """Test with zero timestamp."""
        result = build_md_filename(0, "Test Dialog")
        self.assertTrue(result.startswith("0000-00-00_00-00"))
        self.assertTrue(result.endswith(".md"))

    def test_filename_format(self):
        """Test the overall filename format."""
        ts = 1749736260000
        result = build_md_filename(ts, "Test")
        # Should match pattern: YYYY-MM-DD_HH-MM_Title.md
        self.assertRegex(result, r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}_\w+\.md")


class TestBuildFolderPath(unittest.TestCase):
    """Test build_folder_path function."""

    def test_basic_path(self):
        """Test building a basic folder path."""
        ts = 1749736260000  # 2025-06-12
        result = build_folder_path("myProject", ts)
        self.assertIn("myProject", result)
        # Check year-month component
        self.assertIn("2025-06", result)

    def test_zero_timestamp(self):
        """Test with zero timestamp."""
        result = build_folder_path("myProject", 0)
        self.assertIn("myProject", result)
        self.assertIn("0000-00", result)

    def test_special_project_name(self):
        """Test with special characters in project name."""
        result = build_folder_path("my:project", 1749736260000)
        self.assertNotIn(":", result)


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
        """Test tool call at standard verbosity when rawArgs is already a dict (not JSON string)."""
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
        """Test tool call at full verbosity when result is already a dict (not JSON string)."""
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


class TestExportDialogs(unittest.TestCase):
    """Test export_dialogs function - integration with mock viewer."""

    def _make_viewer_mock(self, dialogs, messages_by_id=None):
        """Create a mock viewer with given dialogs."""
        viewer = MagicMock()
        viewer.get_all_dialogs.return_value = dialogs
        return viewer

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_export_creates_files(self, mock_get_messages, mock_load_config):
        """Test that export creates the correct file structure."""
        mock_load_config.return_value = {
            "export_path": "/tmp/test",
            "verbosity": 2,
        }

        mock_get_messages.return_value = [
            {
                "type": 1, "text": "Hello", "attached_files": [],
                "is_thought": False, "tool_data": None,
            },
            {
                "type": 2, "text": "Hi!", "attached_files": [],
                "is_thought": False, "tool_data": None,
                "token_count": {},
            },
        ]

        dialogs = [
            {
                "composer_id": "abc123",
                "name": "Test Dialog",
                "project_name": "myProject",
                "created_at": 1749736260000,  # 2025-06-12
                "last_updated": 1749736300000,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir)
            viewer = self._make_viewer_mock(dialogs)

            stats = export_dialogs(viewer, export_path=export_path, verbosity=2)

            self.assertEqual(stats["exported"], 1)
            self.assertEqual(stats["errors"], 0)

            # Check folder structure
            project_dir = export_path / "myProject"
            self.assertTrue(project_dir.exists())

            month_dir = project_dir / "2025-06"
            self.assertTrue(month_dir.exists())

            # Check file exists
            md_files = list(month_dir.glob("*.md"))
            self.assertEqual(len(md_files), 1)
            self.assertIn("Test_Dialog", md_files[0].name)

            # Check content
            content = md_files[0].read_text()
            self.assertIn("# Test Dialog", content)
            self.assertIn("Hello", content)
            self.assertIn("Hi!", content)

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_export_empty_dialog_skipped(self, mock_get_messages, mock_load_config):
        """Test that dialogs with no messages are skipped."""
        mock_load_config.return_value = {"export_path": "/tmp", "verbosity": 2}
        mock_get_messages.return_value = []

        dialogs = [
            {
                "composer_id": "abc123",
                "name": "Empty Dialog",
                "project_name": "myProject",
                "created_at": 1749736260000,
                "last_updated": 1749736260000,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            viewer = self._make_viewer_mock(dialogs)
            stats = export_dialogs(viewer, export_path=Path(tmpdir), verbosity=2)
            self.assertEqual(stats["skipped"], 1)
            self.assertEqual(stats["exported"], 0)

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_export_error_handling(self, mock_get_messages, mock_load_config):
        """Test that errors are counted but don't stop export."""
        mock_load_config.return_value = {"export_path": "/tmp", "verbosity": 2}
        mock_get_messages.side_effect = Exception("DB error")

        dialogs = [
            {
                "composer_id": "abc123",
                "name": "Bad Dialog",
                "project_name": "myProject",
                "created_at": 1749736260000,
                "last_updated": 1749736260000,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            viewer = self._make_viewer_mock(dialogs)
            stats = export_dialogs(viewer, export_path=Path(tmpdir), verbosity=2)
            self.assertEqual(stats["errors"], 1)
            self.assertEqual(stats["exported"], 0)

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_export_no_dialogs(self, mock_get_messages, mock_load_config):
        """Test export with no dialogs found."""
        mock_load_config.return_value = {"export_path": "/tmp", "verbosity": 2}

        with tempfile.TemporaryDirectory() as tmpdir:
            viewer = self._make_viewer_mock([])
            stats = export_dialogs(viewer, export_path=Path(tmpdir), verbosity=2)
            self.assertEqual(stats["total_dialogs"], 0)
            self.assertEqual(stats["exported"], 0)

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_export_multiple_projects(self, mock_get_messages, mock_load_config):
        """Test export with multiple projects creates separate folders."""
        mock_load_config.return_value = {"export_path": "/tmp", "verbosity": 2}
        mock_get_messages.return_value = [
            {
                "type": 1, "text": "Test", "attached_files": [],
                "is_thought": False, "tool_data": None,
            },
        ]

        dialogs = [
            {
                "composer_id": "id1",
                "name": "Dialog A",
                "project_name": "ProjectAlpha",
                "created_at": 1749736260000,
                "last_updated": 1749736260000,
            },
            {
                "composer_id": "id2",
                "name": "Dialog B",
                "project_name": "ProjectBeta",
                "created_at": 1749736260000,
                "last_updated": 1749736260000,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir)
            viewer = self._make_viewer_mock(dialogs)
            stats = export_dialogs(viewer, export_path=export_path, verbosity=2)

            self.assertEqual(stats["exported"], 2)
            self.assertTrue((export_path / "ProjectAlpha").exists())
            self.assertTrue((export_path / "ProjectBeta").exists())

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_export_overwrites_existing(self, mock_get_messages, mock_load_config):
        """Test that export overwrites existing files."""
        mock_load_config.return_value = {"export_path": "/tmp", "verbosity": 2}
        mock_get_messages.return_value = [
            {
                "type": 1, "text": "Updated content", "attached_files": [],
                "is_thought": False, "tool_data": None,
            },
        ]

        dialogs = [
            {
                "composer_id": "abc123",
                "name": "Test Dialog",
                "project_name": "myProject",
                "created_at": 1749736260000,
                "last_updated": 1749736260000,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir)
            viewer = self._make_viewer_mock(dialogs)

            # First export
            export_dialogs(viewer, export_path=export_path, verbosity=2)

            # Second export (should overwrite)
            stats = export_dialogs(viewer, export_path=export_path, verbosity=2)
            self.assertEqual(stats["exported"], 1)

            # Check only one file exists
            md_files = list((export_path / "myProject" / "2025-06").glob("*.md"))
            self.assertEqual(len(md_files), 1)
            content = md_files[0].read_text()
            self.assertIn("Updated content", content)


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
