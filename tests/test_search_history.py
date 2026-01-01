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


if __name__ == "__main__":
    unittest.main()
