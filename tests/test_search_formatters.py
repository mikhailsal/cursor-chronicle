"""
Tests for search_history formatting functions.
"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import search_history


class TestHighlightQuery(unittest.TestCase):
    """Test highlight_query function."""

    def test_highlight_query(self):
        """Test query highlighting."""
        text = "Hello KiloCode world"
        highlighted = search_history.highlight_query(text, "KiloCode")
        self.assertIn("\033[1;33m", highlighted)
        self.assertIn("\033[0m", highlighted)
        self.assertIn("KiloCode", highlighted)


class TestFormatSearchResults(unittest.TestCase):
    """Test format_search_results function."""

    def test_format_search_results_empty(self):
        """Test formatting empty results."""
        searcher = search_history.CursorHistorySearch()
        output = search_history.format_search_results([], "test", searcher)
        self.assertIn("No results found", output)

    def test_format_search_results_with_data(self):
        """Test formatting results with data."""
        searcher = search_history.CursorHistorySearch()
        results = [{
            "field": "text",
            "content": "Discussing KiloCode features",
            "type": 1,
            "bubble_id": "bubble1",
            "composer_id": "comp1",
            "project_name": "MyProject",
            "folder_path": "/home/user/MyProject",
            "dialog_name": "KiloCode Discussion",
            "last_updated": 1704067200000,
            "created_at": 1704067200000,
        }]
        output = search_history.format_search_results(results, "KiloCode", searcher)
        self.assertIn("KiloCode", output)
        self.assertIn("MyProject", output)
        self.assertIn("KiloCode Discussion", output)
        self.assertIn("1 match", output)

    def test_format_search_results_with_context(self):
        """Test formatting with context enabled."""
        searcher = search_history.CursorHistorySearch()

        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')

        composer_data = {"fullConversationHeadersOnly": [{"bubbleId": "bubble1"}]}
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("composerData:comp1", json.dumps(composer_data)))

        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("bubbleId:comp1:bubble1", json.dumps({"bubbleId": "bubble1", "text": "Test message", "type": 1})))

        conn.commit()
        conn.close()

        searcher.global_storage_path = Path(db_path)

        results = [{
            "field": "text",
            "content": "KiloCode test",
            "type": 1,
            "bubble_id": "bubble1",
            "composer_id": "comp1",
            "project_name": "Project",
            "folder_path": "/path",
            "dialog_name": "Dialog",
            "last_updated": 1704067200000,
            "created_at": 1704067200000,
        }]

        try:
            output = search_history.format_search_results(results, "KiloCode", searcher, show_context=True)
            self.assertIn("CONTEXT", output)
        finally:
            os.unlink(db_path)

    def test_format_search_results_long_content_truncation(self):
        """Test long content truncation in results."""
        searcher = search_history.CursorHistorySearch()
        long_content = "x" * 600 + "KiloCode" + "y" * 600
        results = [{
            "field": "text",
            "content": long_content,
            "type": 1,
            "bubble_id": "bubble1",
            "composer_id": "comp1",
            "project_name": "Project",
            "folder_path": "/path",
            "dialog_name": "Dialog",
            "last_updated": 1704067200000,
            "created_at": 1704067200000,
        }]
        output = search_history.format_search_results(results, "KiloCode", searcher)
        self.assertIn("...", output)

    def test_format_search_results_tool_type(self):
        """Test formatting tool result type."""
        searcher = search_history.CursorHistorySearch()
        results = [{
            "field": "tool_args",
            "content": '{"path": "kilocode.py"}',
            "tool_name": "read_file",
            "bubble_id": "bubble1",
            "composer_id": "comp1",
            "project_name": "Project",
            "folder_path": "/path",
            "dialog_name": "Dialog",
            "last_updated": 1704067200000,
            "created_at": 0,
        }]
        output = search_history.format_search_results(results, "kilocode", searcher)
        self.assertIn("Tool: read_file", output)

    def test_format_search_results_no_dates(self):
        """Test formatting when dates are missing."""
        searcher = search_history.CursorHistorySearch()
        results = [{
            "field": "text",
            "content": "test",
            "type": 1,
            "bubble_id": "bubble1",
            "composer_id": "comp1",
            "project_name": "Project",
            "folder_path": "/path",
            "dialog_name": "Dialog",
            "last_updated": 0,
            "created_at": 0,
        }]
        output = search_history.format_search_results(results, "test", searcher)
        self.assertIn("Project", output)

    def test_format_search_results_type_2_ai(self):
        """Test AI message type (type 2) icon."""
        searcher = search_history.CursorHistorySearch()
        results = [{
            "field": "text",
            "content": "AI response here",
            "type": 2,
            "bubble_id": "bubble1",
            "composer_id": "comp1",
            "project_name": "Project",
            "folder_path": "/path",
            "dialog_name": "Dialog",
            "last_updated": 1704067200000,
            "created_at": 1704067200000,
        }]
        output = search_history.format_search_results(results, "AI", searcher)
        self.assertIn("🤖 AI", output)


class TestFormatFullDialog(unittest.TestCase):
    """Test format_full_dialog function."""

    def test_format_full_dialog(self):
        """Test formatting full dialog."""
        messages = [
            {"type": 1, "text": "Hello AI", "tool_data": None},
            {"type": 2, "text": "Hi! How can I help?", "tool_data": None},
        ]
        output = search_history.format_full_dialog(messages, "Test Dialog", "TestProject")
        self.assertIn("TestProject", output)
        self.assertIn("Test Dialog", output)
        self.assertIn("USER", output)
        self.assertIn("AI", output)
        self.assertIn("Hello AI", output)
        self.assertIn("Hi! How can I help?", output)

    def test_format_full_dialog_with_tool(self):
        """Test formatting dialog with tool data."""
        messages = [{"type": 2, "text": "", "tool_data": {"name": "read_file", "status": "completed"}}]
        output = search_history.format_full_dialog(messages, "Dialog", "Project")
        self.assertIn("TOOL: read_file", output)

    def test_format_full_dialog_other_type(self):
        """Test formatting dialog with other message type."""
        messages = [{"type": 99, "text": "Unknown type message", "tool_data": None}]
        output = search_history.format_full_dialog(messages, "Dialog", "Project")
        self.assertIn("MESSAGE (type 99)", output)

    def test_format_full_dialog_empty_messages(self):
        """Test formatting dialog with empty messages."""
        messages = [{"type": 1, "text": "", "tool_data": None}]
        output = search_history.format_full_dialog(messages, "Dialog", "Project")
        self.assertIn("Dialog", output)


if __name__ == "__main__":
    unittest.main()
