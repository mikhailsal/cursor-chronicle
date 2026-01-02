#!/usr/bin/env python3
"""
Basic tests for cursor_chronicle module
"""

import os
import sys
import unittest
from pathlib import Path

# Add parent directory to path to import cursor_chronicle
sys.path.insert(0, str(Path(__file__).parent.parent))

import cursor_chronicle


class TestCursorChronicle(unittest.TestCase):
    """Test basic functionality of cursor_chronicle"""

    def test_import(self):
        """Test that cursor_chronicle can be imported"""
        self.assertIsNotNone(cursor_chronicle)

    def test_cursor_chat_viewer_class(self):
        """Test that CursorChatViewer class exists and can be instantiated"""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertIsNotNone(viewer)

    def test_tool_types_mapping(self):
        """Test that tool types mapping is properly defined"""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertIsInstance(viewer.tool_types, dict)
        self.assertGreater(len(viewer.tool_types), 0)

        # Check some known tool types
        self.assertIn(1, viewer.tool_types)
        self.assertIn(15, viewer.tool_types)  # Terminal Command

    def test_config_paths(self):
        """Test that config paths are properly set"""
        viewer = cursor_chronicle.CursorChatViewer()

        # Check that paths are Path objects
        self.assertIsInstance(viewer.cursor_config_path, Path)
        self.assertIsInstance(viewer.workspace_storage_path, Path)
        self.assertIsInstance(viewer.global_storage_path, Path)

        # Check path structure
        self.assertTrue(str(viewer.cursor_config_path).endswith(".config/Cursor/User"))
        self.assertTrue(str(viewer.workspace_storage_path).endswith("workspaceStorage"))
        self.assertTrue(str(viewer.global_storage_path).endswith("state.vscdb"))

    def test_extract_files_from_layout(self):
        """Test the extract_files_from_layout method"""
        viewer = cursor_chronicle.CursorChatViewer()

        # Test with empty layout
        files = viewer.extract_files_from_layout({})
        self.assertEqual(files, [])

        # Test with simple layout
        layout = {
            "src": {"main.py": None, "utils.py": None, "tests": {"test_main.py": None}},
            "README.md": None,
        }

        files = viewer.extract_files_from_layout(layout)
        expected_files = [
            "src/main.py",
            "src/utils.py",
            "src/tests/test_main.py",
            "README.md",
        ]

        # Sort both lists for comparison
        files.sort()
        expected_files.sort()

        self.assertEqual(files, expected_files)

    def test_format_attached_files(self):
        """Test the format_attached_files method"""
        viewer = cursor_chronicle.CursorChatViewer()

        # Test with empty files
        result = viewer.format_attached_files([], 1)
        self.assertEqual(result, "")

        # Test with sample files
        attached_files = [
            {"type": "active", "path": "src/main.py", "line": 42},
            {"type": "selected", "path": "src/utils.py"},
        ]

        result = viewer.format_attached_files(attached_files, 1)
        self.assertIn("Active file: src/main.py", result)
        self.assertIn("Selected file: src/utils.py", result)
        self.assertIn("Line: 42", result)

    def test_infer_model_from_context(self):
        """Test model inference logic"""
        viewer = cursor_chronicle.CursorChatViewer()

        # Test agentic mode detection
        message = {
            "text": "Hello world",
            "is_agentic": True,
            "token_count": {"inputTokens": 100, "outputTokens": 200},
        }

        result = viewer.infer_model_from_context(message, 300)
        self.assertIn("Claude", result)
        self.assertIn("agentic", result)

        # Test high token usage
        message = {
            "text": "Hello world",
            "is_agentic": False,
            "token_count": {"inputTokens": 50000, "outputTokens": 60000},
        }

        result = viewer.infer_model_from_context(message, 110000)
        self.assertIn("Claude", result)
        self.assertIn("high token", result)


class TestListAllDialogs(unittest.TestCase):
    """Test list_all_dialogs and get_all_dialogs functionality"""

    def test_get_all_dialogs_method_exists(self):
        """Test that get_all_dialogs method exists"""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertTrue(hasattr(viewer, "get_all_dialogs"))
        self.assertTrue(callable(viewer.get_all_dialogs))

    def test_list_all_dialogs_method_exists(self):
        """Test that list_all_dialogs method exists"""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertTrue(hasattr(viewer, "list_all_dialogs"))
        self.assertTrue(callable(viewer.list_all_dialogs))

    def test_get_all_dialogs_returns_list(self):
        """Test that get_all_dialogs returns a list"""
        viewer = cursor_chronicle.CursorChatViewer()
        result = viewer.get_all_dialogs()
        self.assertIsInstance(result, list)

    def test_get_all_dialogs_with_date_filtering(self):
        """Test date filtering parameters"""
        from datetime import datetime
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        # Test with start date
        start = datetime(2024, 1, 1)
        result = viewer.get_all_dialogs(start_date=start)
        self.assertIsInstance(result, list)
        
        # All returned dialogs should be after start date
        for dialog in result:
            if dialog.get("last_updated"):
                dialog_date = datetime.fromtimestamp(dialog["last_updated"] / 1000)
                self.assertGreaterEqual(dialog_date, start)

    def test_get_all_dialogs_with_end_date(self):
        """Test end date filtering"""
        from datetime import datetime
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        # Test with end date
        end = datetime(2030, 12, 31)
        result = viewer.get_all_dialogs(end_date=end)
        self.assertIsInstance(result, list)
        
        # All returned dialogs should be before end date
        for dialog in result:
            if dialog.get("last_updated"):
                dialog_date = datetime.fromtimestamp(dialog["last_updated"] / 1000)
                self.assertLessEqual(dialog_date, end)

    def test_get_all_dialogs_with_project_filter(self):
        """Test project name filtering"""
        viewer = cursor_chronicle.CursorChatViewer()
        
        # Get all dialogs first
        all_dialogs = viewer.get_all_dialogs()
        
        if all_dialogs:
            # Use first project name as filter
            project_name = all_dialogs[0].get("project_name", "")
            if project_name:
                filtered = viewer.get_all_dialogs(project_filter=project_name)
                # All filtered dialogs should contain the project name
                for dialog in filtered:
                    self.assertIn(
                        project_name.lower(),
                        dialog["project_name"].lower()
                    )

    def test_get_all_dialogs_date_range(self):
        """Test date range filtering"""
        from datetime import datetime
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        start = datetime(2024, 1, 1)
        end = datetime(2030, 12, 31)
        result = viewer.get_all_dialogs(start_date=start, end_date=end)
        self.assertIsInstance(result, list)
        
        for dialog in result:
            if dialog.get("last_updated"):
                dialog_date = datetime.fromtimestamp(dialog["last_updated"] / 1000)
                self.assertGreaterEqual(dialog_date, start)
                self.assertLessEqual(dialog_date, end)

    def test_get_all_dialogs_sorted_by_created_asc(self):
        """Test that results are sorted by created_at ascending (oldest first) by default"""
        viewer = cursor_chronicle.CursorChatViewer()
        dialogs = viewer.get_all_dialogs()
        
        if len(dialogs) > 1:
            for i in range(len(dialogs) - 1):
                current = dialogs[i].get("created_at", 0)
                next_one = dialogs[i + 1].get("created_at", 0)
                self.assertLessEqual(current, next_one)

    def test_get_all_dialogs_sorted_by_created_desc(self):
        """Test that results can be sorted by created_at descending (newest first)"""
        viewer = cursor_chronicle.CursorChatViewer()
        dialogs = viewer.get_all_dialogs(sort_desc=True)
        
        if len(dialogs) > 1:
            for i in range(len(dialogs) - 1):
                current = dialogs[i].get("created_at", 0)
                next_one = dialogs[i + 1].get("created_at", 0)
                self.assertGreaterEqual(current, next_one)

    def test_get_all_dialogs_sorted_by_updated_asc(self):
        """Test sorting by last_updated ascending with use_updated=True"""
        viewer = cursor_chronicle.CursorChatViewer()
        dialogs = viewer.get_all_dialogs(use_updated=True)
        
        if len(dialogs) > 1:
            for i in range(len(dialogs) - 1):
                current = dialogs[i].get("last_updated", 0)
                next_one = dialogs[i + 1].get("last_updated", 0)
                self.assertLessEqual(current, next_one)

    def test_get_all_dialogs_sorted_by_updated_desc(self):
        """Test sorting by last_updated descending with use_updated=True"""
        viewer = cursor_chronicle.CursorChatViewer()
        dialogs = viewer.get_all_dialogs(use_updated=True, sort_desc=True)
        
        if len(dialogs) > 1:
            for i in range(len(dialogs) - 1):
                current = dialogs[i].get("last_updated", 0)
                next_one = dialogs[i + 1].get("last_updated", 0)
                self.assertGreaterEqual(current, next_one)

    def test_get_all_dialogs_sorted_by_name(self):
        """Test sorting by dialog name"""
        viewer = cursor_chronicle.CursorChatViewer()
        dialogs = viewer.get_all_dialogs(sort_by="name")
        
        if len(dialogs) > 1:
            for i in range(len(dialogs) - 1):
                current = dialogs[i].get("name", "").lower()
                next_one = dialogs[i + 1].get("name", "").lower()
                self.assertLessEqual(current, next_one)

    def test_get_all_dialogs_sorted_by_project(self):
        """Test sorting by project name"""
        viewer = cursor_chronicle.CursorChatViewer()
        dialogs = viewer.get_all_dialogs(sort_by="project")
        
        if len(dialogs) > 1:
            for i in range(len(dialogs) - 1):
                current = dialogs[i].get("project_name", "").lower()
                next_one = dialogs[i + 1].get("project_name", "").lower()
                self.assertLessEqual(current, next_one)

    def test_dialog_dict_structure(self):
        """Test that returned dialog dicts have expected keys"""
        viewer = cursor_chronicle.CursorChatViewer()
        dialogs = viewer.get_all_dialogs()
        
        expected_keys = [
            "composer_id",
            "name",
            "project_name",
            "folder_path",
            "last_updated",
            "created_at",
        ]
        
        for dialog in dialogs:
            for key in expected_keys:
                self.assertIn(key, dialog)


class TestParseDateFunction(unittest.TestCase):
    """Test the parse_date helper function"""

    def test_parse_date_iso_format(self):
        """Test parsing ISO date format"""
        from cursor_chronicle import parse_date
        
        result = parse_date("2024-06-15")
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)

    def test_parse_date_with_time(self):
        """Test parsing date with time"""
        from cursor_chronicle import parse_date
        
        result = parse_date("2024-06-15 14:30")
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.minute, 30)

    def test_parse_date_european_format(self):
        """Test parsing European date format"""
        from cursor_chronicle import parse_date
        
        result = parse_date("15.06.2024")
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)

    def test_parse_date_invalid_raises(self):
        """Test that invalid date raises ArgumentTypeError"""
        import argparse
        from cursor_chronicle import parse_date
        
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_date("invalid-date")


if __name__ == "__main__":
    unittest.main()
