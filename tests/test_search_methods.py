"""
Tests for search_history search methods (search_all, get_dialog_context, get_full_dialog).
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


class TestSearchAllFast(unittest.TestCase):
    """Test search_all_fast method."""

    def test_search_all_fast_no_storage(self):
        """Test search when global storage doesn't exist."""
        searcher = search_history.CursorHistorySearch()
        searcher.global_storage_path = Path("/nonexistent/path/state.vscdb")
        result = searcher.search_all("query")
        self.assertEqual(result, [])

    def test_search_all_fast_with_mock_db(self):
        """Test search_all_fast with mock database."""
        searcher = search_history.CursorHistorySearch()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace1"
            workspace_dir.mkdir()

            workspace_json = workspace_dir / "workspace.json"
            workspace_json.write_text(json.dumps({"folder": "file:///home/user/project"}))

            state_db = workspace_dir / "state.vscdb"
            conn = sqlite3.connect(state_db)
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE ItemTable (key TEXT, value TEXT)')
            cursor.execute("INSERT INTO ItemTable VALUES (?, ?)",
                           ("composer.composerData", json.dumps({
                               "allComposers": [{"composerId": "comp1", "name": "Test Dialog", "lastUpdatedAt": 1704067200000, "createdAt": 1704067200000}]
                           })))
            conn.commit()
            conn.close()

            global_db = Path(tmpdir) / "global.vscdb"
            conn = sqlite3.connect(global_db)
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')
            cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                           ("bubbleId:comp1:bubble1", json.dumps({"bubbleId": "bubble1", "text": "KiloCode implementation " + "x" * 100, "type": 1})))
            conn.commit()
            conn.close()

            searcher.workspace_storage_path = Path(tmpdir)
            searcher.global_storage_path = global_db

            results = searcher.search_all("KiloCode", verbose=True)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["project_name"], "project")

    def test_search_all_fast_with_project_filter(self):
        """Test search_all_fast with project filter."""
        searcher = search_history.CursorHistorySearch()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace1"
            workspace_dir.mkdir()

            workspace_json = workspace_dir / "workspace.json"
            workspace_json.write_text(json.dumps({"folder": "file:///home/user/myproject"}))

            state_db = workspace_dir / "state.vscdb"
            conn = sqlite3.connect(state_db)
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE ItemTable (key TEXT, value TEXT)')
            cursor.execute("INSERT INTO ItemTable VALUES (?, ?)",
                           ("composer.composerData", json.dumps({"allComposers": [{"composerId": "comp1", "name": "Test", "lastUpdatedAt": 1704067200000}]})))
            conn.commit()
            conn.close()

            global_db = Path(tmpdir) / "global.vscdb"
            conn = sqlite3.connect(global_db)
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')
            cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                           ("bubbleId:comp1:bubble1", json.dumps({"bubbleId": "bubble1", "text": "KiloCode " + "x" * 100, "type": 1})))
            conn.commit()
            conn.close()

            searcher.workspace_storage_path = Path(tmpdir)
            searcher.global_storage_path = global_db

            results = searcher.search_all("KiloCode", project_filter="myproject")
            self.assertEqual(len(results), 1)

            results = searcher.search_all("KiloCode", project_filter="other")
            self.assertEqual(len(results), 0)

    def test_search_all_fast_limit_results(self):
        """Test result limiting."""
        searcher = search_history.CursorHistorySearch()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace1"
            workspace_dir.mkdir()

            workspace_json = workspace_dir / "workspace.json"
            workspace_json.write_text(json.dumps({"folder": "file:///home/user/project"}))

            state_db = workspace_dir / "state.vscdb"
            conn = sqlite3.connect(state_db)
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE ItemTable (key TEXT, value TEXT)')
            cursor.execute("INSERT INTO ItemTable VALUES (?, ?)",
                           ("composer.composerData", json.dumps({"allComposers": [{"composerId": "comp1", "name": "Test", "lastUpdatedAt": 1704067200000}]})))
            conn.commit()
            conn.close()

            global_db = Path(tmpdir) / "global.vscdb"
            conn = sqlite3.connect(global_db)
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')

            for i in range(10):
                cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                               (f"bubbleId:comp1:bubble{i}", json.dumps({"bubbleId": f"bubble{i}", "text": f"KiloCode message {i} " + "x" * 100, "type": 1})))
            conn.commit()
            conn.close()

            searcher.workspace_storage_path = Path(tmpdir)
            searcher.global_storage_path = global_db

            results = searcher.search_all("KiloCode", limit=3)
            self.assertEqual(len(results), 3)


class TestGetDialogContext(unittest.TestCase):
    """Test get_dialog_context method."""

    def test_get_dialog_context_no_storage(self):
        """Test when global storage doesn't exist."""
        searcher = search_history.CursorHistorySearch()
        searcher.global_storage_path = Path("/nonexistent/path/state.vscdb")
        result = searcher.get_dialog_context("comp1", "bubble1")
        self.assertEqual(result, [])

    def test_get_dialog_context_bubble_not_found(self):
        """Test when bubble is not found in order."""
        searcher = search_history.CursorHistorySearch()

        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')
        composer_data = {"fullConversationHeadersOnly": [{"bubbleId": "other_bubble"}]}
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("composerData:comp1", json.dumps(composer_data)))
        conn.commit()
        conn.close()

        searcher.global_storage_path = Path(db_path)

        try:
            result = searcher.get_dialog_context("comp1", "nonexistent")
            self.assertEqual(result, [])
        finally:
            os.unlink(db_path)

    def test_get_dialog_context_with_context(self):
        """Test getting dialog context."""
        searcher = search_history.CursorHistorySearch()

        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')

        composer_data = {"fullConversationHeadersOnly": [{"bubbleId": "bubble1"}, {"bubbleId": "bubble2"}, {"bubbleId": "bubble3"}], "padding": "x" * 100}
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("composerData:comp1", json.dumps(composer_data)))

        for i in range(1, 4):
            cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                           (f"bubbleId:comp1:bubble{i}", json.dumps({"bubbleId": f"bubble{i}", "text": f"Message {i} " + "x" * 100, "type": 1 if i % 2 else 2})))

        conn.commit()
        conn.close()

        searcher.global_storage_path = Path(db_path)

        try:
            result = searcher.get_dialog_context("comp1", "bubble2", context_size=1)
            self.assertEqual(len(result), 3)
            self.assertTrue(result[1]["is_target"])
        finally:
            os.unlink(db_path)


class TestGetFullDialog(unittest.TestCase):
    """Test get_full_dialog method."""

    def test_get_full_dialog_no_storage(self):
        """Test when global storage doesn't exist."""
        searcher = search_history.CursorHistorySearch()
        searcher.global_storage_path = Path("/nonexistent/path/state.vscdb")
        result = searcher.get_full_dialog("comp1")
        self.assertEqual(result, [])

    def test_get_full_dialog_with_ordered_bubbles(self):
        """Test getting full dialog with ordered bubbles."""
        searcher = search_history.CursorHistorySearch()

        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')

        composer_data = {"fullConversationHeadersOnly": [{"bubbleId": "bubble1"}, {"bubbleId": "bubble2"}], "padding": "x" * 100}
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("composerData:comp1", json.dumps(composer_data)))

        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("bubbleId:comp1:bubble1", json.dumps({"bubbleId": "bubble1", "text": "Hello " + "x" * 100, "type": 1})))
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("bubbleId:comp1:bubble2", json.dumps({"bubbleId": "bubble2", "text": "Hi there! " + "x" * 100, "type": 2})))

        conn.commit()
        conn.close()

        searcher.global_storage_path = Path(db_path)

        try:
            result = searcher.get_full_dialog("comp1")
            self.assertEqual(len(result), 2)
            self.assertIn("Hello", result[0]["text"])
            self.assertIn("Hi there!", result[1]["text"])
        finally:
            os.unlink(db_path)

    def test_get_full_dialog_fallback_rowid_order(self):
        """Test getting full dialog with fallback to rowid order."""
        searcher = search_history.CursorHistorySearch()

        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')

        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("bubbleId:comp1:bubble1", json.dumps({"bubbleId": "bubble1", "text": "First " + "x" * 100, "type": 1})))
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("bubbleId:comp1:bubble2", json.dumps({"bubbleId": "bubble2", "text": "Second " + "x" * 100, "type": 2})))

        conn.commit()
        conn.close()

        searcher.global_storage_path = Path(db_path)

        try:
            result = searcher.get_full_dialog("comp1")
            self.assertEqual(len(result), 2)
        finally:
            os.unlink(db_path)

    def test_get_full_dialog_with_tool_data(self):
        """Test getting dialog with tool data."""
        searcher = search_history.CursorHistorySearch()

        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')

        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("bubbleId:comp1:bubble1", json.dumps({"bubbleId": "bubble1", "text": "", "type": 2, "toolFormerData": {"name": "read_file", "padding": "x" * 100}})))

        conn.commit()
        conn.close()

        searcher.global_storage_path = Path(db_path)

        try:
            result = searcher.get_full_dialog("comp1")
            self.assertEqual(len(result), 1)
            self.assertIsNotNone(result[0]["tool_data"])
        finally:
            os.unlink(db_path)


if __name__ == "__main__":
    unittest.main()
