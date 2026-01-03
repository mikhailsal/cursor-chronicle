"""
Tests for search_history core functionality.
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


class TestSearchHistory(unittest.TestCase):
    """Test search_history basic functionality."""

    def test_import(self):
        """Test that search_history can be imported."""
        self.assertIsNotNone(search_history)

    def test_cursor_history_search_class(self):
        """Test CursorHistorySearch class instantiation."""
        searcher = search_history.CursorHistorySearch()
        self.assertIsNotNone(searcher)

    def test_config_paths(self):
        """Test config paths are properly set."""
        searcher = search_history.CursorHistorySearch()
        self.assertIsInstance(searcher.cursor_config_path, Path)
        self.assertIsInstance(searcher.workspace_storage_path, Path)
        self.assertIsInstance(searcher.global_storage_path, Path)


class TestSearchInBubble(unittest.TestCase):
    """Test search_in_bubble method."""

    def test_search_in_bubble_text(self):
        """Test search in bubble text field."""
        searcher = search_history.CursorHistorySearch()
        bubble = {"text": "Let's discuss KiloCode implementation", "type": 1}
        matches = searcher.search_in_bubble(bubble, "KiloCode")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["field"], "text")

    def test_search_in_bubble_case_insensitive(self):
        """Test case insensitive search."""
        searcher = search_history.CursorHistorySearch()
        bubble = {"text": "Let's discuss KiloCode implementation", "type": 1}
        matches = searcher.search_in_bubble(bubble, "kilocode")
        self.assertEqual(len(matches), 1)

    def test_search_in_bubble_case_sensitive(self):
        """Test case sensitive search."""
        searcher = search_history.CursorHistorySearch()
        bubble = {"text": "Let's discuss KiloCode implementation", "type": 1}
        matches = searcher.search_in_bubble(bubble, "kilocode", case_sensitive=True)
        self.assertEqual(len(matches), 0)

    def test_search_in_bubble_tool_data(self):
        """Test search in bubble tool data."""
        searcher = search_history.CursorHistorySearch()
        bubble = {
            "text": "",
            "type": 2,
            "toolFormerData": {
                "name": "read_file",
                "rawArgs": '{"path": "kilocode/main.py"}',
                "result": '{"contents": "# KiloCode main file"}',
            },
        }
        matches = searcher.search_in_bubble(bubble, "kilocode")
        self.assertEqual(len(matches), 2)
        fields = [m["field"] for m in matches]
        self.assertIn("tool_args", fields)
        self.assertIn("tool_result", fields)

    def test_search_in_bubble_no_match(self):
        """Test search with no matches."""
        searcher = search_history.CursorHistorySearch()
        bubble = {"text": "Hello world", "type": 1}
        matches = searcher.search_in_bubble(bubble, "kilocode")
        self.assertEqual(len(matches), 0)

    def test_search_in_bubble_empty(self):
        """Test search in empty bubble."""
        searcher = search_history.CursorHistorySearch()
        bubble = {}
        matches = searcher.search_in_bubble(bubble, "test")
        self.assertEqual(len(matches), 0)

    def test_search_in_bubble_thinking_dict(self):
        """Test search in thinking data as dict."""
        searcher = search_history.CursorHistorySearch()
        bubble = {"text": "", "type": 2, "thinking": {"content": "Thinking about KiloCode implementation"}}
        matches = searcher.search_in_bubble(bubble, "KiloCode")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["field"], "thinking")

    def test_search_in_bubble_thinking_dict_text_field(self):
        """Test search in thinking data with text field."""
        searcher = search_history.CursorHistorySearch()
        bubble = {"text": "", "type": 2, "thinking": {"text": "KiloCode analysis"}}
        matches = searcher.search_in_bubble(bubble, "KiloCode")
        self.assertEqual(len(matches), 1)

    def test_search_in_bubble_thinking_string(self):
        """Test search in thinking data as string."""
        searcher = search_history.CursorHistorySearch()
        bubble = {"text": "", "type": 2, "thinking": "Direct KiloCode thinking string"}
        matches = searcher.search_in_bubble(bubble, "KiloCode")
        self.assertEqual(len(matches), 1)

    def test_search_in_bubble_tool_data_empty(self):
        """Test search with empty tool data."""
        searcher = search_history.CursorHistorySearch()
        bubble = {"text": "", "type": 2, "toolFormerData": {}}
        matches = searcher.search_in_bubble(bubble, "test")
        self.assertEqual(len(matches), 0)


class TestSearchComposer(unittest.TestCase):
    """Test search_composer method."""

    def test_search_composer_no_global_storage(self):
        """Test search when global storage doesn't exist."""
        searcher = search_history.CursorHistorySearch()
        searcher.global_storage_path = Path("/nonexistent/path/state.vscdb")
        result = searcher.search_composer("test_id", "query")
        self.assertEqual(result, [])

    def test_search_composer_with_mock_db(self):
        """Test search_composer with mock database."""
        searcher = search_history.CursorHistorySearch()

        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')

        bubble_data = {"bubbleId": "bubble1", "text": "KiloCode implementation details " + "x" * 100, "type": 1}
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("bubbleId:composer1:bubble1", json.dumps(bubble_data)))

        conn.commit()
        conn.close()

        searcher.global_storage_path = Path(db_path)

        try:
            results = searcher.search_composer("composer1", "KiloCode")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["bubble_id"], "bubble1")
            self.assertEqual(results[0]["composer_id"], "composer1")
        finally:
            os.unlink(db_path)

    def test_search_composer_json_decode_error(self):
        """Test JSON decode error handling."""
        searcher = search_history.CursorHistorySearch()

        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("bubbleId:composer1:bubble1", "invalid json " + "x" * 100))
        conn.commit()
        conn.close()

        searcher.global_storage_path = Path(db_path)

        try:
            results = searcher.search_composer("composer1", "json")
            self.assertEqual(len(results), 0)
        finally:
            os.unlink(db_path)


class TestGetAllComposers(unittest.TestCase):
    """Test get_all_composers method."""

    def test_get_all_composers_no_workspace(self):
        """Test when workspace storage doesn't exist."""
        searcher = search_history.CursorHistorySearch()
        searcher.workspace_storage_path = Path("/nonexistent/path")
        result = searcher.get_all_composers()
        self.assertEqual(result, [])

    def test_get_all_composers_with_mock_workspace(self):
        """Test getting composers from mock workspace."""
        searcher = search_history.CursorHistorySearch()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace1"
            workspace_dir.mkdir()

            workspace_json = workspace_dir / "workspace.json"
            workspace_json.write_text(json.dumps({"folder": "remote://server/project"}))

            state_db = workspace_dir / "state.vscdb"
            conn = sqlite3.connect(state_db)
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE ItemTable (key TEXT, value TEXT)')
            cursor.execute("INSERT INTO ItemTable VALUES (?, ?)",
                           ("composer.composerData", json.dumps({"allComposers": [{"composerId": "comp1", "name": "Test"}]})))
            conn.commit()
            conn.close()

            searcher.workspace_storage_path = Path(tmpdir)
            composers = searcher.get_all_composers()
            self.assertEqual(len(composers), 1)
            self.assertEqual(composers[0]["_project_name"], "remote://server/project")

    def test_get_all_composers_skip_non_directory(self):
        """Test that non-directories are skipped."""
        searcher = search_history.CursorHistorySearch()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "not_a_dir.txt"
            file_path.write_text("test")
            searcher.workspace_storage_path = Path(tmpdir)
            composers = searcher.get_all_composers()
            self.assertEqual(composers, [])

    def test_get_all_composers_skip_missing_files(self):
        """Test that workspaces with missing files are skipped."""
        searcher = search_history.CursorHistorySearch()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace1"
            workspace_dir.mkdir()
            searcher.workspace_storage_path = Path(tmpdir)
            composers = searcher.get_all_composers()
            self.assertEqual(composers, [])

    def test_get_all_composers_exception_handling(self):
        """Test that exceptions in workspace processing are handled."""
        searcher = search_history.CursorHistorySearch()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace1"
            workspace_dir.mkdir()

            workspace_json = workspace_dir / "workspace.json"
            workspace_json.write_text("invalid json")

            state_db = workspace_dir / "state.vscdb"
            conn = sqlite3.connect(state_db)
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE ItemTable (key TEXT, value TEXT)')
            conn.commit()
            conn.close()

            searcher.workspace_storage_path = Path(tmpdir)
            composers = searcher.get_all_composers()
            self.assertEqual(composers, [])


class TestSearchHistoryIntegration(unittest.TestCase):
    """Integration tests that require actual Cursor data."""

    def setUp(self):
        """Check if Cursor data exists."""
        self.searcher = search_history.CursorHistorySearch()
        self.has_data = self.searcher.global_storage_path.exists()

    def test_get_all_composers(self):
        """Test getting composers from workspace."""
        if not self.has_data:
            self.skipTest("No Cursor data available")
        composers = self.searcher.get_all_composers()
        self.assertIsInstance(composers, list)


if __name__ == "__main__":
    unittest.main()
