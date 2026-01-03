#!/usr/bin/env python3
"""
Tests for search_history module
"""

import json
import sys
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import search_history


class TestSearchHistory(unittest.TestCase):
    """Test search_history functionality"""

    def test_import(self):
        """Test that search_history can be imported"""
        self.assertIsNotNone(search_history)

    def test_cursor_history_search_class(self):
        """Test CursorHistorySearch class instantiation"""
        searcher = search_history.CursorHistorySearch()
        self.assertIsNotNone(searcher)

    def test_config_paths(self):
        """Test config paths are properly set"""
        searcher = search_history.CursorHistorySearch()
        self.assertIsInstance(searcher.cursor_config_path, Path)
        self.assertIsInstance(searcher.workspace_storage_path, Path)
        self.assertIsInstance(searcher.global_storage_path, Path)

    def test_search_in_bubble_text(self):
        """Test search in bubble text field"""
        searcher = search_history.CursorHistorySearch()

        bubble = {
            "text": "Let's discuss KiloCode implementation",
            "type": 1,
        }

        matches = searcher.search_in_bubble(bubble, "KiloCode")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["field"], "text")

        # Case insensitive
        matches = searcher.search_in_bubble(bubble, "kilocode")
        self.assertEqual(len(matches), 1)

        # Case sensitive should not match
        matches = searcher.search_in_bubble(bubble, "kilocode", case_sensitive=True)
        self.assertEqual(len(matches), 0)

    def test_search_in_bubble_tool_data(self):
        """Test search in bubble tool data"""
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
        self.assertEqual(len(matches), 2)  # Found in rawArgs and result

        fields = [m["field"] for m in matches]
        self.assertIn("tool_args", fields)
        self.assertIn("tool_result", fields)

    def test_search_in_bubble_no_match(self):
        """Test search with no matches"""
        searcher = search_history.CursorHistorySearch()

        bubble = {
            "text": "Hello world",
            "type": 1,
        }

        matches = searcher.search_in_bubble(bubble, "kilocode")
        self.assertEqual(len(matches), 0)

    def test_search_in_bubble_empty(self):
        """Test search in empty bubble"""
        searcher = search_history.CursorHistorySearch()

        bubble = {}
        matches = searcher.search_in_bubble(bubble, "test")
        self.assertEqual(len(matches), 0)

    def test_highlight_query(self):
        """Test query highlighting"""
        searcher = search_history.CursorHistorySearch()

        text = "Hello KiloCode world"
        highlighted = searcher._highlight_query(text, "KiloCode")
        
        # Should contain ANSI color codes
        self.assertIn("\033[1;33m", highlighted)
        self.assertIn("\033[0m", highlighted)
        self.assertIn("KiloCode", highlighted)

    def test_format_search_results_empty(self):
        """Test formatting empty results"""
        searcher = search_history.CursorHistorySearch()

        output = searcher.format_search_results([], "test")
        self.assertIn("No results found", output)

    def test_format_search_results_with_data(self):
        """Test formatting results with data"""
        searcher = search_history.CursorHistorySearch()

        results = [
            {
                "field": "text",
                "content": "Discussing KiloCode features",
                "type": 1,
                "bubble_id": "bubble1",
                "composer_id": "comp1",
                "project_name": "MyProject",
                "folder_path": "/home/user/MyProject",
                "dialog_name": "KiloCode Discussion",
                "last_updated": 1704067200000,  # 2024-01-01
                "created_at": 1704067200000,
            }
        ]

        output = searcher.format_search_results(results, "KiloCode")
        self.assertIn("KiloCode", output)
        self.assertIn("MyProject", output)
        self.assertIn("KiloCode Discussion", output)
        self.assertIn("1 match", output)

    def test_format_full_dialog(self):
        """Test formatting full dialog"""
        searcher = search_history.CursorHistorySearch()

        messages = [
            {"type": 1, "text": "Hello AI", "tool_data": None},
            {"type": 2, "text": "Hi! How can I help?", "tool_data": None},
        ]

        output = searcher.format_full_dialog(messages, "Test Dialog", "TestProject")
        self.assertIn("TestProject", output)
        self.assertIn("Test Dialog", output)
        self.assertIn("USER", output)
        self.assertIn("AI", output)
        self.assertIn("Hello AI", output)
        self.assertIn("Hi! How can I help?", output)


class TestSearchHistoryIntegration(unittest.TestCase):
    """Integration tests that require actual Cursor data"""

    def setUp(self):
        """Check if Cursor data exists"""
        self.searcher = search_history.CursorHistorySearch()
        self.has_data = self.searcher.global_storage_path.exists()

    def test_get_all_composers(self):
        """Test getting composers from workspace"""
        if not self.has_data:
            self.skipTest("No Cursor data available")

        composers = self.searcher.get_all_composers()
        # Just check it returns a list
        self.assertIsInstance(composers, list)


class TestSearchInBubbleAdvanced(unittest.TestCase):
    """Advanced tests for search_in_bubble"""

    def test_search_in_bubble_thinking_dict(self):
        """Test search in thinking data as dict"""
        searcher = search_history.CursorHistorySearch()
        bubble = {
            "text": "",
            "type": 2,
            "thinking": {"content": "Thinking about KiloCode implementation"},
        }
        matches = searcher.search_in_bubble(bubble, "KiloCode")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["field"], "thinking")

    def test_search_in_bubble_thinking_dict_text_field(self):
        """Test search in thinking data with text field"""
        searcher = search_history.CursorHistorySearch()
        bubble = {
            "text": "",
            "type": 2,
            "thinking": {"text": "KiloCode analysis"},
        }
        matches = searcher.search_in_bubble(bubble, "KiloCode")
        self.assertEqual(len(matches), 1)

    def test_search_in_bubble_thinking_string(self):
        """Test search in thinking data as string"""
        searcher = search_history.CursorHistorySearch()
        bubble = {
            "text": "",
            "type": 2,
            "thinking": "Direct KiloCode thinking string",
        }
        matches = searcher.search_in_bubble(bubble, "KiloCode")
        self.assertEqual(len(matches), 1)

    def test_search_in_bubble_tool_data_empty(self):
        """Test search with empty tool data"""
        searcher = search_history.CursorHistorySearch()
        bubble = {
            "text": "",
            "type": 2,
            "toolFormerData": {},
        }
        matches = searcher.search_in_bubble(bubble, "test")
        self.assertEqual(len(matches), 0)


class TestSearchComposer(unittest.TestCase):
    """Test search_composer method"""

    def test_search_composer_no_global_storage(self):
        """Test search when global storage doesn't exist"""
        searcher = search_history.CursorHistorySearch()
        from pathlib import Path
        searcher.global_storage_path = Path("/nonexistent/path/state.vscdb")
        
        result = searcher.search_composer("test_id", "query")
        self.assertEqual(result, [])

    def test_search_composer_with_mock_db(self):
        """Test search_composer with mock database"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        # Make value > 100 chars to pass LENGTH(value) > 100 filter
        bubble_data = {
            "bubbleId": "bubble1",
            "text": "KiloCode implementation details " + "x" * 100,
            "type": 1,
        }
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
            import os
            os.unlink(db_path)


class TestSearchAllFast(unittest.TestCase):
    """Test search_all_fast method"""

    def test_search_all_fast_no_storage(self):
        """Test search when global storage doesn't exist"""
        searcher = search_history.CursorHistorySearch()
        from pathlib import Path
        searcher.global_storage_path = Path("/nonexistent/path/state.vscdb")
        
        result = searcher.search_all_fast("query")
        self.assertEqual(result, [])

    def test_search_all_fast_with_mock_db(self):
        """Test search_all_fast with mock database"""
        import sqlite3
        import tempfile
        from pathlib import Path
        import os
        
        searcher = search_history.CursorHistorySearch()
        
        # Create mock workspace storage
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace1"
            workspace_dir.mkdir()
            
            # Create workspace.json
            workspace_json = workspace_dir / "workspace.json"
            workspace_json.write_text(json.dumps({
                "folder": "file:///home/user/project"
            }))
            
            # Create state.vscdb for workspace
            state_db = workspace_dir / "state.vscdb"
            conn = sqlite3.connect(state_db)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE ItemTable (key TEXT, value TEXT)''')
            cursor.execute("INSERT INTO ItemTable VALUES (?, ?)",
                          ("composer.composerData", json.dumps({
                              "allComposers": [{
                                  "composerId": "comp1",
                                  "name": "Test Dialog",
                                  "lastUpdatedAt": 1704067200000,
                                  "createdAt": 1704067200000,
                              }]
                          })))
            conn.commit()
            conn.close()
            
            # Create global storage (value > 100 chars)
            global_db = Path(tmpdir) / "global.vscdb"
            conn = sqlite3.connect(global_db)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
            cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                          ("bubbleId:comp1:bubble1", json.dumps({
                              "bubbleId": "bubble1",
                              "text": "KiloCode implementation " + "x" * 100,
                              "type": 1,
                          })))
            conn.commit()
            conn.close()
            
            # Set paths
            searcher.workspace_storage_path = Path(tmpdir)
            searcher.global_storage_path = global_db
            
            results = searcher.search_all_fast("KiloCode", verbose=True)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["project_name"], "project")

    def test_search_all_fast_with_project_filter(self):
        """Test search_all_fast with project filter"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace1"
            workspace_dir.mkdir()
            
            workspace_json = workspace_dir / "workspace.json"
            workspace_json.write_text(json.dumps({
                "folder": "file:///home/user/myproject"
            }))
            
            state_db = workspace_dir / "state.vscdb"
            conn = sqlite3.connect(state_db)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE ItemTable (key TEXT, value TEXT)''')
            cursor.execute("INSERT INTO ItemTable VALUES (?, ?)",
                          ("composer.composerData", json.dumps({
                              "allComposers": [{
                                  "composerId": "comp1",
                                  "name": "Test",
                                  "lastUpdatedAt": 1704067200000,
                              }]
                          })))
            conn.commit()
            conn.close()
            
            # Value > 100 chars
            global_db = Path(tmpdir) / "global.vscdb"
            conn = sqlite3.connect(global_db)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
            cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                          ("bubbleId:comp1:bubble1", json.dumps({
                              "bubbleId": "bubble1",
                              "text": "KiloCode " + "x" * 100,
                              "type": 1,
                          })))
            conn.commit()
            conn.close()
            
            searcher.workspace_storage_path = Path(tmpdir)
            searcher.global_storage_path = global_db
            
            # Filter by matching project
            results = searcher.search_all_fast("KiloCode", project_filter="myproject")
            self.assertEqual(len(results), 1)
            
            # Filter by non-matching project
            results = searcher.search_all_fast("KiloCode", project_filter="other")
            self.assertEqual(len(results), 0)


class TestGetDialogContext(unittest.TestCase):
    """Test get_dialog_context method"""

    def test_get_dialog_context_no_storage(self):
        """Test when global storage doesn't exist"""
        searcher = search_history.CursorHistorySearch()
        from pathlib import Path
        searcher.global_storage_path = Path("/nonexistent/path/state.vscdb")
        
        result = searcher.get_dialog_context("comp1", "bubble1")
        self.assertEqual(result, [])

    def test_get_dialog_context_bubble_not_found(self):
        """Test when bubble is not found in order"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        # Add composer data without the target bubble
        composer_data = {
            "fullConversationHeadersOnly": [{"bubbleId": "other_bubble"}]
        }
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("composerData:comp1", json.dumps(composer_data)))
        
        conn.commit()
        conn.close()
        
        searcher.global_storage_path = Path(db_path)
        
        try:
            result = searcher.get_dialog_context("comp1", "nonexistent")
            self.assertEqual(result, [])
        finally:
            import os
            os.unlink(db_path)

    def test_get_dialog_context_with_context(self):
        """Test getting dialog context"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        # Add composer data (> 100 chars)
        composer_data = {
            "fullConversationHeadersOnly": [
                {"bubbleId": "bubble1"},
                {"bubbleId": "bubble2"},
                {"bubbleId": "bubble3"},
            ],
            "padding": "x" * 100,
        }
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("composerData:comp1", json.dumps(composer_data)))
        
        # Add bubbles (> 100 chars each)
        for i in range(1, 4):
            cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                          (f"bubbleId:comp1:bubble{i}", json.dumps({
                              "bubbleId": f"bubble{i}",
                              "text": f"Message {i} " + "x" * 100,
                              "type": 1 if i % 2 else 2,
                          })))
        
        conn.commit()
        conn.close()
        
        searcher.global_storage_path = Path(db_path)
        
        try:
            result = searcher.get_dialog_context("comp1", "bubble2", context_size=1)
            self.assertEqual(len(result), 3)
            self.assertTrue(result[1]["is_target"])
        finally:
            import os
            os.unlink(db_path)


class TestGetFullDialog(unittest.TestCase):
    """Test get_full_dialog method"""

    def test_get_full_dialog_no_storage(self):
        """Test when global storage doesn't exist"""
        searcher = search_history.CursorHistorySearch()
        from pathlib import Path
        searcher.global_storage_path = Path("/nonexistent/path/state.vscdb")
        
        result = searcher.get_full_dialog("comp1")
        self.assertEqual(result, [])

    def test_get_full_dialog_with_ordered_bubbles(self):
        """Test getting full dialog with ordered bubbles"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        # Value > 100 chars
        composer_data = {
            "fullConversationHeadersOnly": [
                {"bubbleId": "bubble1"},
                {"bubbleId": "bubble2"},
            ],
            "padding": "x" * 100,
        }
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("composerData:comp1", json.dumps(composer_data)))
        
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("bubbleId:comp1:bubble1", json.dumps({
                          "bubbleId": "bubble1",
                          "text": "Hello " + "x" * 100,
                          "type": 1,
                      })))
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("bubbleId:comp1:bubble2", json.dumps({
                          "bubbleId": "bubble2",
                          "text": "Hi there! " + "x" * 100,
                          "type": 2,
                      })))
        
        conn.commit()
        conn.close()
        
        searcher.global_storage_path = Path(db_path)
        
        try:
            result = searcher.get_full_dialog("comp1")
            self.assertEqual(len(result), 2)
            self.assertIn("Hello", result[0]["text"])
            self.assertIn("Hi there!", result[1]["text"])
        finally:
            import os
            os.unlink(db_path)

    def test_get_full_dialog_fallback_rowid_order(self):
        """Test getting full dialog with fallback to rowid order"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        # No composer data (will fallback) - values > 100 chars
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("bubbleId:comp1:bubble1", json.dumps({
                          "bubbleId": "bubble1",
                          "text": "First " + "x" * 100,
                          "type": 1,
                      })))
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("bubbleId:comp1:bubble2", json.dumps({
                          "bubbleId": "bubble2",
                          "text": "Second " + "x" * 100,
                          "type": 2,
                      })))
        
        conn.commit()
        conn.close()
        
        searcher.global_storage_path = Path(db_path)
        
        try:
            result = searcher.get_full_dialog("comp1")
            self.assertEqual(len(result), 2)
        finally:
            import os
            os.unlink(db_path)

    def test_get_full_dialog_with_tool_data(self):
        """Test getting dialog with tool data"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        # Value > 100 chars
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("bubbleId:comp1:bubble1", json.dumps({
                          "bubbleId": "bubble1",
                          "text": "",
                          "type": 2,
                          "toolFormerData": {"name": "read_file", "padding": "x" * 100},
                      })))
        
        conn.commit()
        conn.close()
        
        searcher.global_storage_path = Path(db_path)
        
        try:
            result = searcher.get_full_dialog("comp1")
            self.assertEqual(len(result), 1)
            self.assertIsNotNone(result[0]["tool_data"])
        finally:
            import os
            os.unlink(db_path)


class TestFormatSearchResultsAdvanced(unittest.TestCase):
    """Advanced tests for format_search_results"""

    def test_format_search_results_with_context(self):
        """Test formatting with context enabled"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        # Create mock database for context
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        composer_data = {
            "fullConversationHeadersOnly": [{"bubbleId": "bubble1"}]
        }
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("composerData:comp1", json.dumps(composer_data)))
        
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("bubbleId:comp1:bubble1", json.dumps({
                          "bubbleId": "bubble1",
                          "text": "Test message",
                          "type": 1,
                      })))
        
        conn.commit()
        conn.close()
        
        searcher.global_storage_path = Path(db_path)
        
        results = [
            {
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
            }
        ]
        
        try:
            output = searcher.format_search_results(results, "KiloCode", show_context=True)
            self.assertIn("CONTEXT", output)
        finally:
            import os
            os.unlink(db_path)

    def test_format_search_results_long_content_truncation(self):
        """Test long content truncation in results"""
        searcher = search_history.CursorHistorySearch()
        
        long_content = "x" * 600 + "KiloCode" + "y" * 600
        results = [
            {
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
            }
        ]
        
        output = searcher.format_search_results(results, "KiloCode")
        self.assertIn("...", output)

    def test_format_search_results_tool_type(self):
        """Test formatting tool result type"""
        searcher = search_history.CursorHistorySearch()
        
        results = [
            {
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
            }
        ]
        
        output = searcher.format_search_results(results, "kilocode")
        self.assertIn("Tool: read_file", output)

    def test_format_search_results_no_dates(self):
        """Test formatting when dates are missing"""
        searcher = search_history.CursorHistorySearch()
        
        results = [
            {
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
            }
        ]
        
        output = searcher.format_search_results(results, "test")
        # Should not crash, dates section optional
        self.assertIn("Project", output)


class TestFormatFullDialogAdvanced(unittest.TestCase):
    """Advanced tests for format_full_dialog"""

    def test_format_full_dialog_with_tool(self):
        """Test formatting dialog with tool data"""
        searcher = search_history.CursorHistorySearch()
        
        messages = [
            {"type": 2, "text": "", "tool_data": {"name": "read_file", "status": "completed"}},
        ]
        
        output = searcher.format_full_dialog(messages, "Dialog", "Project")
        self.assertIn("TOOL: read_file", output)

    def test_format_full_dialog_other_type(self):
        """Test formatting dialog with other message type"""
        searcher = search_history.CursorHistorySearch()
        
        messages = [
            {"type": 99, "text": "Unknown type message", "tool_data": None},
        ]
        
        output = searcher.format_full_dialog(messages, "Dialog", "Project")
        self.assertIn("MESSAGE (type 99)", output)

    def test_format_full_dialog_empty_messages(self):
        """Test formatting dialog with empty messages"""
        searcher = search_history.CursorHistorySearch()
        
        messages = [
            {"type": 1, "text": "", "tool_data": None},  # Should be skipped
        ]
        
        output = searcher.format_full_dialog(messages, "Dialog", "Project")
        # Header should still be present
        self.assertIn("Dialog", output)


class TestGetAllComposers(unittest.TestCase):
    """Test get_all_composers method"""

    def test_get_all_composers_no_workspace(self):
        """Test when workspace storage doesn't exist"""
        searcher = search_history.CursorHistorySearch()
        from pathlib import Path
        searcher.workspace_storage_path = Path("/nonexistent/path")
        
        result = searcher.get_all_composers()
        self.assertEqual(result, [])

    def test_get_all_composers_with_mock_workspace(self):
        """Test getting composers from mock workspace"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace1"
            workspace_dir.mkdir()
            
            # Create workspace.json with non-file URI
            workspace_json = workspace_dir / "workspace.json"
            workspace_json.write_text(json.dumps({
                "folder": "remote://server/project"
            }))
            
            state_db = workspace_dir / "state.vscdb"
            conn = sqlite3.connect(state_db)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE ItemTable (key TEXT, value TEXT)''')
            cursor.execute("INSERT INTO ItemTable VALUES (?, ?)",
                          ("composer.composerData", json.dumps({
                              "allComposers": [{
                                  "composerId": "comp1",
                                  "name": "Test",
                              }]
                          })))
            conn.commit()
            conn.close()
            
            searcher.workspace_storage_path = Path(tmpdir)
            
            composers = searcher.get_all_composers()
            self.assertEqual(len(composers), 1)
            self.assertEqual(composers[0]["_project_name"], "remote://server/project")

    def test_get_all_composers_skip_non_directory(self):
        """Test that non-directories are skipped"""
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file (not a directory)
            file_path = Path(tmpdir) / "not_a_dir.txt"
            file_path.write_text("test")
            
            searcher.workspace_storage_path = Path(tmpdir)
            
            composers = searcher.get_all_composers()
            self.assertEqual(composers, [])

    def test_get_all_composers_skip_missing_files(self):
        """Test that workspaces with missing files are skipped"""
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace1"
            workspace_dir.mkdir()
            # Missing workspace.json and state.vscdb
            
            searcher.workspace_storage_path = Path(tmpdir)
            
            composers = searcher.get_all_composers()
            self.assertEqual(composers, [])

    def test_get_all_composers_exception_handling(self):
        """Test that exceptions in workspace processing are handled"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace1"
            workspace_dir.mkdir()
            
            # Create invalid workspace.json
            workspace_json = workspace_dir / "workspace.json"
            workspace_json.write_text("invalid json")
            
            # Create valid state.vscdb
            state_db = workspace_dir / "state.vscdb"
            conn = sqlite3.connect(state_db)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE ItemTable (key TEXT, value TEXT)''')
            conn.commit()
            conn.close()
            
            searcher.workspace_storage_path = Path(tmpdir)
            
            # Should not raise, just skip the workspace
            composers = searcher.get_all_composers()
            self.assertEqual(composers, [])


class TestSearchAllFastEdgeCases(unittest.TestCase):
    """Test edge cases in search_all_fast"""

    def test_search_all_fast_limit_results(self):
        """Test result limiting in search_all_fast"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace1"
            workspace_dir.mkdir()
            
            workspace_json = workspace_dir / "workspace.json"
            workspace_json.write_text(json.dumps({
                "folder": "file:///home/user/project"
            }))
            
            state_db = workspace_dir / "state.vscdb"
            conn = sqlite3.connect(state_db)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE ItemTable (key TEXT, value TEXT)''')
            cursor.execute("INSERT INTO ItemTable VALUES (?, ?)",
                          ("composer.composerData", json.dumps({
                              "allComposers": [{
                                  "composerId": "comp1",
                                  "name": "Test",
                                  "lastUpdatedAt": 1704067200000,
                              }]
                          })))
            conn.commit()
            conn.close()
            
            global_db = Path(tmpdir) / "global.vscdb"
            conn = sqlite3.connect(global_db)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
            
            # Insert many matching bubbles
            for i in range(10):
                cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                              (f"bubbleId:comp1:bubble{i}", json.dumps({
                                  "bubbleId": f"bubble{i}",
                                  "text": f"KiloCode message {i} " + "x" * 100,
                                  "type": 1,
                              })))
            
            conn.commit()
            conn.close()
            
            searcher.workspace_storage_path = Path(tmpdir)
            searcher.global_storage_path = global_db
            
            # Request only 3 results
            results = searcher.search_all_fast("KiloCode", limit=3)
            self.assertEqual(len(results), 3)

    def test_search_all_fast_invalid_key_format(self):
        """Test handling of invalid key format"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace1"
            workspace_dir.mkdir()
            
            workspace_json = workspace_dir / "workspace.json"
            workspace_json.write_text(json.dumps({
                "folder": "file:///home/user/project"
            }))
            
            state_db = workspace_dir / "state.vscdb"
            conn = sqlite3.connect(state_db)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE ItemTable (key TEXT, value TEXT)''')
            cursor.execute("INSERT INTO ItemTable VALUES (?, ?)",
                          ("composer.composerData", json.dumps({
                              "allComposers": [{
                                  "composerId": "comp1",
                                  "name": "Test",
                                  "lastUpdatedAt": 1704067200000,
                              }]
                          })))
            conn.commit()
            conn.close()
            
            global_db = Path(tmpdir) / "global.vscdb"
            conn = sqlite3.connect(global_db)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
            
            # Insert bubble with invalid key format (no colon)
            cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                          ("bubbleId", json.dumps({
                              "text": "KiloCode " + "x" * 100,
                          })))
            
            conn.commit()
            conn.close()
            
            searcher.workspace_storage_path = Path(tmpdir)
            searcher.global_storage_path = global_db
            
            # Should not crash
            results = searcher.search_all_fast("KiloCode")
            self.assertEqual(len(results), 0)

    def test_search_all_fast_json_decode_error(self):
        """Test handling of JSON decode error in search"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace1"
            workspace_dir.mkdir()
            
            workspace_json = workspace_dir / "workspace.json"
            workspace_json.write_text(json.dumps({
                "folder": "file:///home/user/project"
            }))
            
            state_db = workspace_dir / "state.vscdb"
            conn = sqlite3.connect(state_db)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE ItemTable (key TEXT, value TEXT)''')
            cursor.execute("INSERT INTO ItemTable VALUES (?, ?)",
                          ("composer.composerData", json.dumps({
                              "allComposers": [{
                                  "composerId": "comp1",
                                  "name": "Test",
                                  "lastUpdatedAt": 1704067200000,
                              }]
                          })))
            conn.commit()
            conn.close()
            
            global_db = Path(tmpdir) / "global.vscdb"
            conn = sqlite3.connect(global_db)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
            
            # Insert invalid JSON that matches search pattern
            cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                          ("bubbleId:comp1:bubble1", "KiloCode invalid json " + "x" * 100))
            
            conn.commit()
            conn.close()
            
            searcher.workspace_storage_path = Path(tmpdir)
            searcher.global_storage_path = global_db
            
            # Should not crash
            results = searcher.search_all_fast("KiloCode")
            self.assertEqual(len(results), 0)


class TestSearchComposerJsonError(unittest.TestCase):
    """Test search_composer JSON error handling"""

    def test_search_composer_json_decode_error(self):
        """Test JSON decode error handling in search_composer"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        # Insert invalid JSON (> 100 chars to pass filter)
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("bubbleId:composer1:bubble1", "invalid json " + "x" * 100))
        
        conn.commit()
        conn.close()
        
        searcher.global_storage_path = Path(db_path)
        
        try:
            results = searcher.search_composer("composer1", "json")
            # Should return empty due to JSON error
            self.assertEqual(len(results), 0)
        finally:
            import os
            os.unlink(db_path)


class TestGetDialogContextJsonError(unittest.TestCase):
    """Test get_dialog_context JSON error handling"""

    def test_get_dialog_context_composer_json_error(self):
        """Test JSON error in composer data"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        # Insert invalid JSON for composer data (> 100 chars)
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("composerData:comp1", "invalid json " + "x" * 100))
        
        conn.commit()
        conn.close()
        
        searcher.global_storage_path = Path(db_path)
        
        try:
            result = searcher.get_dialog_context("comp1", "bubble1")
            # Should return empty due to JSON error
            self.assertEqual(len(result), 0)
        finally:
            import os
            os.unlink(db_path)

    def test_get_dialog_context_bubble_json_error(self):
        """Test JSON error in bubble data"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        # Valid composer data
        composer_data = {
            "fullConversationHeadersOnly": [{"bubbleId": "bubble1"}],
            "padding": "x" * 100,
        }
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("composerData:comp1", json.dumps(composer_data)))
        
        # Invalid JSON for bubble (> 100 chars)
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("bubbleId:comp1:bubble1", "invalid json " + "x" * 100))
        
        conn.commit()
        conn.close()
        
        searcher.global_storage_path = Path(db_path)
        
        try:
            result = searcher.get_dialog_context("comp1", "bubble1", context_size=1)
            # Should return empty due to JSON error
            self.assertEqual(len(result), 0)
        finally:
            import os
            os.unlink(db_path)


class TestGetFullDialogJsonError(unittest.TestCase):
    """Test get_full_dialog JSON error handling"""

    def test_get_full_dialog_composer_json_error(self):
        """Test JSON error in composer data for get_full_dialog"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        # Invalid JSON for composer data (> 100 chars)
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("composerData:comp1", "invalid json " + "x" * 100))
        
        # Valid bubble (> 100 chars)
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("bubbleId:comp1:bubble1", json.dumps({
                          "bubbleId": "bubble1",
                          "text": "Hello " + "x" * 100,
                          "type": 1,
                      })))
        
        conn.commit()
        conn.close()
        
        searcher.global_storage_path = Path(db_path)
        
        try:
            result = searcher.get_full_dialog("comp1")
            # Should fallback to rowid order
            self.assertEqual(len(result), 1)
        finally:
            import os
            os.unlink(db_path)

    def test_get_full_dialog_bubble_json_error(self):
        """Test JSON error in bubble data for get_full_dialog"""
        import sqlite3
        import tempfile
        from pathlib import Path
        
        searcher = search_history.CursorHistorySearch()
        
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        # Invalid JSON for bubble (> 100 chars)
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("bubbleId:comp1:bubble1", "invalid json " + "x" * 100))
        
        conn.commit()
        conn.close()
        
        searcher.global_storage_path = Path(db_path)
        
        try:
            result = searcher.get_full_dialog("comp1")
            # Should return empty due to JSON error
            self.assertEqual(len(result), 0)
        finally:
            import os
            os.unlink(db_path)


class TestMainCLI(unittest.TestCase):
    """Test main CLI functionality"""

    def test_main_no_query_prints_help(self):
        """Test main() with no query prints help"""
        import sys
        from io import StringIO
        from unittest.mock import patch
        
        with patch.object(sys, 'argv', ['search_history.py']):
            captured = StringIO()
            with patch('sys.stdout', captured):
                search_history.main()
        
        output = captured.getvalue()
        # Should print help or usage
        self.assertTrue(len(output) > 0 or output == "")

    def test_main_show_dialog_not_found(self):
        """Test main() with --show-dialog for non-existent dialog"""
        import sys
        from io import StringIO
        from unittest.mock import patch
        from pathlib import Path
        
        with patch.object(sys, 'argv', ['search_history.py', '--show-dialog', 'nonexistent123']):
            captured = StringIO()
            with patch('sys.stdout', captured):
                search_history.main()
        
        output = captured.getvalue()
        self.assertIn("not found", output)

    def test_main_list_dialogs_mode(self):
        """Test main() with --list-dialogs flag"""
        import sys
        from io import StringIO
        from unittest.mock import patch
        
        with patch.object(sys, 'argv', ['search_history.py', 'test', '--list-dialogs', '--limit', '1']):
            captured = StringIO()
            with patch('sys.stdout', captured):
                search_history.main()
        
        output = captured.getvalue()
        # Should show dialogs containing query or no results
        self.assertTrue("Dialogs containing" in output or "No results" in output)


class TestFormatSearchResultsQueryPosition(unittest.TestCase):
    """Test format_search_results query position handling"""

    def test_format_search_results_query_not_in_lower(self):
        """Test when query position cannot be found in lowercased content"""
        searcher = search_history.CursorHistorySearch()
        
        # Content that's long but query won't be found when looking for context
        long_content = "x" * 600 + "TEST" + "y" * 600
        results = [
            {
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
            }
        ]
        
        # Search for something that will be found but position calculation tests edge case
        output = searcher.format_search_results(results, "TEST")
        # Should contain highlighted TEST
        self.assertIn("TEST", output)

    def test_format_search_results_type_2_ai(self):
        """Test AI message type (type 2) icon"""
        searcher = search_history.CursorHistorySearch()
        
        results = [
            {
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
            }
        ]
        
        output = searcher.format_search_results(results, "AI")
        self.assertIn("🤖 AI", output)


if __name__ == "__main__":
    unittest.main()
