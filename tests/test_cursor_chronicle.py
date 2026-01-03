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


class TestStatisticsFeature(unittest.TestCase):
    """Test the statistics functionality"""

    def test_get_dialog_statistics_method_exists(self):
        """Test that get_dialog_statistics method exists"""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertTrue(hasattr(viewer, "get_dialog_statistics"))
        self.assertTrue(callable(viewer.get_dialog_statistics))

    def test_format_statistics_method_exists(self):
        """Test that format_statistics method exists"""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertTrue(hasattr(viewer, "format_statistics"))
        self.assertTrue(callable(viewer.format_statistics))

    def test_show_statistics_method_exists(self):
        """Test that show_statistics method exists"""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertTrue(hasattr(viewer, "show_statistics"))
        self.assertTrue(callable(viewer.show_statistics))

    def test_get_dialog_statistics_returns_dict(self):
        """Test that get_dialog_statistics returns a dictionary with date filter"""
        from datetime import datetime, timedelta
        
        viewer = cursor_chronicle.CursorChatViewer()
        # Use date filter to avoid processing all 1700+ dialogs
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        result = viewer.get_dialog_statistics(start_date=start_date, end_date=end_date)
        self.assertIsInstance(result, dict)

    def test_get_dialog_statistics_has_required_keys(self):
        """Test that statistics dict has required keys"""
        from datetime import datetime, timedelta
        
        viewer = cursor_chronicle.CursorChatViewer()
        # Use date filter to limit scope
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        result = viewer.get_dialog_statistics(start_date=start_date, end_date=end_date)
        
        required_keys = [
            "period_start",
            "period_end",
            "total_dialogs",
            "projects",
        ]
        
        for key in required_keys:
            self.assertIn(key, result)

    def test_get_dialog_statistics_with_date_filter(self):
        """Test statistics with date filtering"""
        from datetime import datetime, timedelta
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        result = viewer.get_dialog_statistics(
            start_date=start_date,
            end_date=end_date
        )
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["period_start"], start_date)
        self.assertEqual(result["period_end"], end_date)

    def test_get_dialog_statistics_with_project_filter(self):
        """Test statistics with project filtering"""
        from datetime import datetime, timedelta
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        # Use date filter + project filter to limit scope
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Get all projects first
        projects = viewer.get_projects()
        if projects:
            project_name = projects[0]["project_name"]
            result = viewer.get_dialog_statistics(
                start_date=start_date,
                end_date=end_date,
                project_filter=project_name
            )
            
            self.assertIsInstance(result, dict)
            # All projects in stats should match the filter
            for proj_name in result.get("projects", {}).keys():
                self.assertIn(project_name.lower(), proj_name.lower())

    def test_format_statistics_empty_stats(self):
        """Test format_statistics with empty data"""
        viewer = cursor_chronicle.CursorChatViewer()
        
        empty_stats = {
            "period_start": None,
            "period_end": None,
            "total_dialogs": 0,
            "projects": {},
        }
        
        result = viewer.format_statistics(empty_stats)
        self.assertIn("No dialogs found", result)

    def test_format_statistics_with_data(self):
        """Test format_statistics with sample data"""
        viewer = cursor_chronicle.CursorChatViewer()
        from datetime import datetime
        from collections import Counter
        
        sample_stats = {
            "period_start": datetime(2024, 1, 1),
            "period_end": datetime(2024, 1, 31),
            "total_dialogs": 5,
            "total_messages": 100,
            "user_messages": 30,
            "ai_messages": 70,
            "tool_calls": 50,
            "thinking_bubbles": 10,
            "total_tokens_in": 10000,
            "total_tokens_out": 5000,
            "total_thinking_time_ms": 30000,
            "projects": {
                "test-project": {
                    "dialogs": 5,
                    "messages": 100,
                    "user_messages": 30,
                    "ai_messages": 70,
                    "tool_calls": 50,
                    "tokens_in": 10000,
                    "tokens_out": 5000,
                    "dialog_names": ["Dialog 1", "Dialog 2"],
                }
            },
            "tool_usage": Counter({"read_file": 20, "edit_file": 30}),
            "daily_activity": {"2024-01-15": {"dialogs": 2, "messages": 40}},
            "dialogs_by_length": [("Dialog 1", "test-project", 60)],
        }
        
        result = viewer.format_statistics(sample_stats)
        
        # Check key sections are present
        self.assertIn("USAGE STATISTICS", result)
        self.assertIn("SUMMARY", result)
        self.assertIn("Total dialogs:", result)
        self.assertIn("5", result)
        self.assertIn("PROJECT ACTIVITY", result)
        self.assertIn("test-project", result)

    def test_statistics_counts_are_non_negative(self):
        """Test that all counts in statistics are non-negative"""
        from datetime import datetime, timedelta
        
        viewer = cursor_chronicle.CursorChatViewer()
        # Use date filter to limit scope
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        result = viewer.get_dialog_statistics(start_date=start_date, end_date=end_date)
        
        if result["total_dialogs"] > 0:
            self.assertGreaterEqual(result.get("total_messages", 0), 0)
            self.assertGreaterEqual(result.get("user_messages", 0), 0)
            self.assertGreaterEqual(result.get("ai_messages", 0), 0)
            self.assertGreaterEqual(result.get("tool_calls", 0), 0)
            self.assertGreaterEqual(result.get("total_tokens_in", 0), 0)
            self.assertGreaterEqual(result.get("total_tokens_out", 0), 0)

    def test_format_statistics_shows_coding_days(self):
        """Test that format_statistics shows coding days percentage"""
        from datetime import datetime
        from collections import Counter
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        # Sample stats with 3 active days out of 10 day period
        # period_end is exclusive, so Jan 1 to Jan 11 = 10 days
        sample_stats = {
            "period_start": datetime(2024, 1, 1),
            "period_end": datetime(2024, 1, 11),  # 10 days period (exclusive end)
            "total_dialogs": 5,
            "total_messages": 100,
            "user_messages": 30,
            "ai_messages": 70,
            "tool_calls": 50,
            "thinking_bubbles": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_thinking_time_ms": 0,
            "projects": {},
            "tool_usage": Counter(),
            "daily_activity": {
                "2024-01-02": {"dialogs": 2, "messages": 40},
                "2024-01-05": {"dialogs": 1, "messages": 30},
                "2024-01-08": {"dialogs": 2, "messages": 30},
            },  # 3 active days
            "dialogs_by_length": [],
        }
        
        result = viewer.format_statistics(sample_stats)
        
        # Should show 3/10 coding days (30%)
        self.assertIn("Coding days:", result)
        self.assertIn("3/10", result)
        self.assertIn("30%", result)

    def test_format_statistics_coding_days_without_dates(self):
        """Test coding days display when no period dates"""
        from collections import Counter
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        sample_stats = {
            "period_start": None,
            "period_end": None,
            "total_dialogs": 5,
            "total_messages": 100,
            "user_messages": 30,
            "ai_messages": 70,
            "tool_calls": 50,
            "thinking_bubbles": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_thinking_time_ms": 0,
            "projects": {},
            "tool_usage": Counter(),
            "daily_activity": {
                "2024-01-02": {"dialogs": 2, "messages": 40},
                "2024-01-05": {"dialogs": 1, "messages": 30},
            },
            "dialogs_by_length": [],
        }
        
        result = viewer.format_statistics(sample_stats)
        
        # Should show just the count without percentage
        self.assertIn("Coding days:", result)
        self.assertIn("2", result)

    def test_daily_activity_in_stats(self):
        """Test that daily_activity is properly populated in statistics"""
        from datetime import datetime, timedelta
        
        viewer = cursor_chronicle.CursorChatViewer()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        result = viewer.get_dialog_statistics(start_date=start_date, end_date=end_date)
        
        # daily_activity should be a dict
        self.assertIn("daily_activity", result)
        self.assertIsInstance(result["daily_activity"], dict)
        
        # If there are dialogs, daily_activity should have entries
        if result["total_dialogs"] > 0:
            self.assertGreater(len(result["daily_activity"]), 0)

    def test_coding_days_month_calculation(self):
        """Test that coding days correctly calculates month boundaries.
        
        Bug fix: --from 2025-05-01 --before 2025-06-01 should show 31 days (May),
        not 32. The --before date is exclusive.
        """
        from datetime import datetime
        from collections import Counter
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        # May 1 to June 1 (exclusive) = 31 days
        sample_stats = {
            "period_start": datetime(2025, 5, 1),
            "period_end": datetime(2025, 6, 1),
            "total_dialogs": 10,
            "total_messages": 100,
            "user_messages": 30,
            "ai_messages": 70,
            "tool_calls": 50,
            "thinking_bubbles": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_thinking_time_ms": 0,
            "projects": {},
            "tool_usage": Counter(),
            "daily_activity": {f"2025-05-{i:02d}": {"dialogs": 1, "messages": 5} for i in range(1, 28)},
            "dialogs_by_length": [],
        }
        
        result = viewer.format_statistics(sample_stats)
        
        # Should show 27/31 (May has 31 days, not 32)
        self.assertIn("27/31", result)
        self.assertNotIn("/32", result)


class TestExtractAttachedFiles(unittest.TestCase):
    """Test extract_attached_files method"""

    def test_extract_attached_files_empty(self):
        """Test with empty bubble data"""
        viewer = cursor_chronicle.CursorChatViewer()
        result = viewer.extract_attached_files({})
        self.assertEqual(result, [])

    def test_extract_attached_files_current_file(self):
        """Test extracting current file location"""
        viewer = cursor_chronicle.CursorChatViewer()
        bubble_data = {
            "currentFileLocationData": {
                "uri": "/path/to/file.py",
                "line": 42,
                "preview": "def test():",
            }
        }
        result = viewer.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "active")
        self.assertEqual(result[0]["path"], "/path/to/file.py")
        self.assertEqual(result[0]["line"], 42)

    def test_extract_attached_files_current_file_path_field(self):
        """Test extracting current file with path field"""
        viewer = cursor_chronicle.CursorChatViewer()
        bubble_data = {
            "currentFileLocationData": {
                "path": "/path/to/file.py",
            }
        }
        result = viewer.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["path"], "/path/to/file.py")

    def test_extract_attached_files_current_file_filepath_field(self):
        """Test extracting current file with filePath field"""
        viewer = cursor_chronicle.CursorChatViewer()
        bubble_data = {
            "currentFileLocationData": {
                "filePath": "/path/to/file.py",
            }
        }
        result = viewer.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["path"], "/path/to/file.py")

    def test_extract_attached_files_current_file_file_field(self):
        """Test extracting current file with file field"""
        viewer = cursor_chronicle.CursorChatViewer()
        bubble_data = {
            "currentFileLocationData": {
                "file": "/path/to/file.py",
            }
        }
        result = viewer.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["path"], "/path/to/file.py")

    def test_extract_attached_files_project_layouts_string(self):
        """Test extracting files from project layouts as JSON string"""
        import json
        viewer = cursor_chronicle.CursorChatViewer()
        layout = {"src": {"main.py": None}}
        bubble_data = {
            "projectLayouts": [json.dumps(layout)]
        }
        result = viewer.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "project")
        self.assertEqual(result[0]["path"], "src/main.py")

    def test_extract_attached_files_project_layouts_invalid_json(self):
        """Test handling invalid JSON in project layouts"""
        viewer = cursor_chronicle.CursorChatViewer()
        bubble_data = {
            "projectLayouts": ["invalid json {"]
        }
        result = viewer.extract_attached_files(bubble_data)
        self.assertEqual(result, [])

    def test_extract_attached_files_project_layouts_dict(self):
        """Test extracting files from project layouts as dict"""
        viewer = cursor_chronicle.CursorChatViewer()
        bubble_data = {
            "projectLayouts": [{"src": {"main.py": None}}]
        }
        result = viewer.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "project")

    def test_extract_attached_files_codebase_context_chunks(self):
        """Test extracting codebase context chunks"""
        viewer = cursor_chronicle.CursorChatViewer()
        bubble_data = {
            "codebaseContextChunks": [
                {
                    "relativeWorkspacePath": "src/utils.py",
                    "contents": "def helper():",
                    "lineRange": "10-20",
                }
            ]
        }
        result = viewer.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "context")
        self.assertEqual(result[0]["path"], "src/utils.py")
        self.assertEqual(result[0]["content"], "def helper():")

    def test_extract_attached_files_relevant_files_dict(self):
        """Test extracting relevant files as dict"""
        viewer = cursor_chronicle.CursorChatViewer()
        bubble_data = {
            "relevantFiles": [
                {"path": "/path/to/file1.py"},
                {"uri": "/path/to/file2.py"},
            ]
        }
        result = viewer.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["type"], "relevant")
        self.assertEqual(result[1]["type"], "relevant")

    def test_extract_attached_files_relevant_files_string(self):
        """Test extracting relevant files as string"""
        viewer = cursor_chronicle.CursorChatViewer()
        bubble_data = {
            "relevantFiles": ["/path/to/file.py"]
        }
        result = viewer.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "relevant")
        self.assertEqual(result[0]["path"], "/path/to/file.py")

    def test_extract_attached_files_attached_code_chunks(self):
        """Test extracting attached code chunks"""
        viewer = cursor_chronicle.CursorChatViewer()
        bubble_data = {
            "attachedCodeChunks": [
                {
                    "path": "/path/to/file.py",
                    "content": "def test():",
                    "selection": "1-10",
                }
            ]
        }
        result = viewer.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "selected")
        self.assertEqual(result[0]["path"], "/path/to/file.py")

    def test_extract_attached_files_context_file_selections(self):
        """Test extracting file selections from context"""
        viewer = cursor_chronicle.CursorChatViewer()
        bubble_data = {
            "context": {
                "fileSelections": [
                    {"path": "/path/to/file.py", "selection": "1-10"}
                ]
            }
        }
        result = viewer.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "selected_context")


class TestFormatToolCall(unittest.TestCase):
    """Test format_tool_call method"""

    def test_format_tool_call_empty(self):
        """Test with empty tool data"""
        viewer = cursor_chronicle.CursorChatViewer()
        result = viewer.format_tool_call({}, 1)
        self.assertEqual(result, "")

    def test_format_tool_call_null_tool(self):
        """Test with null tool field"""
        viewer = cursor_chronicle.CursorChatViewer()
        result = viewer.format_tool_call({"tool": None}, 1)
        self.assertEqual(result, "")

    def test_format_tool_call_basic(self):
        """Test basic tool call formatting"""
        viewer = cursor_chronicle.CursorChatViewer()
        tool_data = {
            "tool": 5,  # Read File
            "name": "read_file",
            "status": "completed",
            "userDecision": "accepted",
        }
        result = viewer.format_tool_call(tool_data, 1)
        self.assertIn("TOOL", result)
        self.assertIn("Read File", result)
        self.assertIn("read_file", result)
        self.assertIn("completed", result)
        self.assertIn("✅", result)

    def test_format_tool_call_rejected(self):
        """Test tool call with rejected decision"""
        viewer = cursor_chronicle.CursorChatViewer()
        tool_data = {
            "tool": 7,  # Edit File
            "name": "edit_file",
            "status": "completed",
            "userDecision": "rejected",
        }
        result = viewer.format_tool_call(tool_data, 1)
        self.assertIn("❌", result)

    def test_format_tool_call_unknown_tool_type(self):
        """Test with unknown tool type"""
        viewer = cursor_chronicle.CursorChatViewer()
        tool_data = {
            "tool": 999,
            "name": "unknown_tool",
            "status": "completed",
        }
        result = viewer.format_tool_call(tool_data, 1)
        self.assertIn("Tool 999", result)

    def test_format_tool_call_with_raw_args(self):
        """Test tool call with raw arguments"""
        import json
        viewer = cursor_chronicle.CursorChatViewer()
        tool_data = {
            "tool": 5,
            "name": "read_file",
            "status": "completed",
            "rawArgs": json.dumps({"path": "/path/to/file.py"}),
        }
        result = viewer.format_tool_call(tool_data, 1)
        self.assertIn("path", result)
        self.assertIn("/path/to/file.py", result)

    def test_format_tool_call_with_explanation(self):
        """Test tool call with explanation (not truncated)"""
        import json
        viewer = cursor_chronicle.CursorChatViewer()
        long_explanation = "x" * 200
        tool_data = {
            "tool": 5,
            "name": "read_file",
            "status": "completed",
            "rawArgs": json.dumps({"explanation": long_explanation}),
        }
        result = viewer.format_tool_call(tool_data, 1)
        # Explanation should not be truncated
        self.assertIn(long_explanation, result)

    def test_format_tool_call_code_edit_truncation(self):
        """Test code_edit truncation in edit_file"""
        import json
        viewer = cursor_chronicle.CursorChatViewer()
        code_edit = "\n".join([f"line {i}" for i in range(100)])
        tool_data = {
            "tool": 7,
            "name": "edit_file",
            "status": "completed",
            "rawArgs": json.dumps({"code_edit": code_edit}),
        }
        result = viewer.format_tool_call(tool_data, 5)
        self.assertIn("more lines", result)

    def test_format_tool_call_long_param_truncation(self):
        """Test long parameter truncation"""
        import json
        viewer = cursor_chronicle.CursorChatViewer()
        long_value = "x" * 200
        tool_data = {
            "tool": 5,
            "name": "read_file",
            "status": "completed",
            "rawArgs": json.dumps({"path": long_value}),
        }
        result = viewer.format_tool_call(tool_data, 1)
        self.assertIn("...", result)

    def test_format_tool_call_read_file_result(self):
        """Test read_file result formatting"""
        import json
        viewer = cursor_chronicle.CursorChatViewer()
        contents = "\n".join([f"line {i}" for i in range(100)])
        tool_data = {
            "tool": 5,
            "name": "read_file",
            "status": "completed",
            "result": json.dumps({"contents": contents, "file": "/test.py"}),
        }
        result = viewer.format_tool_call(tool_data, 5)
        self.assertIn("more lines", result)
        self.assertIn("file", result)

    def test_format_tool_call_terminal_cmd_result(self):
        """Test run_terminal_cmd result formatting"""
        import json
        viewer = cursor_chronicle.CursorChatViewer()
        output = "\n".join([f"output line {i}" for i in range(100)])
        tool_data = {
            "tool": 15,
            "name": "run_terminal_cmd",
            "status": "completed",
            "result": json.dumps({"output": output, "exitCodeV2": 0}),
        }
        result = viewer.format_tool_call(tool_data, 5)
        self.assertIn("Exit code: 0", result)
        self.assertIn("more lines", result)

    def test_format_tool_call_edit_file_diff_result(self):
        """Test edit_file diff result formatting"""
        import json
        viewer = cursor_chronicle.CursorChatViewer()
        tool_data = {
            "tool": 7,
            "name": "edit_file",
            "status": "completed",
            "result": json.dumps({
                "diff": {
                    "chunks": [
                        {"linesAdded": 5, "linesRemoved": 3, "diffString": "+new\n-old"}
                    ]
                }
            }),
        }
        # With max_output_lines=1
        result1 = viewer.format_tool_call(tool_data, 1)
        self.assertIn("+5 -3", result1)
        self.assertIn("details hidden", result1)
        
        # With max_output_lines>1
        result2 = viewer.format_tool_call(tool_data, 10)
        self.assertIn("+new", result2)

    def test_format_tool_call_generic_result(self):
        """Test generic result formatting"""
        import json
        viewer = cursor_chronicle.CursorChatViewer()
        tool_data = {
            "tool": 1,
            "name": "search",
            "status": "completed",
            "result": json.dumps({"key1": "value1", "key2": "value2", "key3": "value3"}),
        }
        result = viewer.format_tool_call(tool_data, 2)
        self.assertIn("key1", result)
        self.assertIn("key2", result)

    def test_format_tool_call_generic_result_truncation(self):
        """Test generic result truncation"""
        import json
        viewer = cursor_chronicle.CursorChatViewer()
        long_value = "x" * 200
        tool_data = {
            "tool": 1,
            "name": "search",
            "status": "completed",
            "result": json.dumps({"key": long_value}),
        }
        result = viewer.format_tool_call(tool_data, 10)
        self.assertIn("...", result)

    def test_format_tool_call_result_as_string(self):
        """Test result as non-dict JSON"""
        import json
        viewer = cursor_chronicle.CursorChatViewer()
        result_str = "\n".join([f"line {i}" for i in range(100)])
        tool_data = {
            "tool": 1,
            "name": "test_tool",
            "status": "completed",
            "result": json.dumps(result_str),
        }
        result = viewer.format_tool_call(tool_data, 5)
        self.assertIn("more lines", result)


class TestFormatTokenInfo(unittest.TestCase):
    """Test format_token_info method"""

    def test_format_token_info_empty(self):
        """Test with empty message"""
        viewer = cursor_chronicle.CursorChatViewer()
        result = viewer.format_token_info({})
        self.assertEqual(result, "")

    def test_format_token_info_with_tokens(self):
        """Test with token count"""
        viewer = cursor_chronicle.CursorChatViewer()
        message = {
            "token_count": {"inputTokens": 100, "outputTokens": 50},
        }
        result = viewer.format_token_info(message)
        self.assertIn("Tokens:", result)
        self.assertIn("100→50", result)
        self.assertIn("150 total", result)

    def test_format_token_info_agentic(self):
        """Test with agentic mode"""
        viewer = cursor_chronicle.CursorChatViewer()
        message = {"is_agentic": True}
        result = viewer.format_token_info(message)
        self.assertIn("Agentic mode: enabled", result)

    def test_format_token_info_unified_mode(self):
        """Test with unified mode"""
        viewer = cursor_chronicle.CursorChatViewer()
        message = {"unified_mode": 4}
        result = viewer.format_token_info(message)
        self.assertIn("Unified mode: 4", result)

    def test_format_token_info_web_search(self):
        """Test with web search"""
        viewer = cursor_chronicle.CursorChatViewer()
        message = {"use_web": True}
        result = viewer.format_token_info(message)
        self.assertIn("Web search: used", result)

    def test_format_token_info_capabilities(self):
        """Test with capabilities"""
        viewer = cursor_chronicle.CursorChatViewer()
        message = {"capabilities_ran": {"cap1": True, "cap2": True, "cap3": True, "cap4": True}}
        result = viewer.format_token_info(message)
        self.assertIn("Capabilities:", result)
        self.assertIn("and 1 more", result)

    def test_format_token_info_refunded(self):
        """Test with refunded status"""
        viewer = cursor_chronicle.CursorChatViewer()
        message = {"is_refunded": True}
        result = viewer.format_token_info(message)
        self.assertIn("refunded", result)

    def test_format_token_info_usage_uuid(self):
        """Test with usage UUID"""
        viewer = cursor_chronicle.CursorChatViewer()
        message = {"usage_uuid": "12345678-abcd-efgh-ijkl-mnopqrstuvwx"}
        result = viewer.format_token_info(message)
        self.assertIn("Usage ID: 12345678", result)


class TestInferModelFromContext(unittest.TestCase):
    """Test infer_model_from_context method"""

    def test_infer_claude_from_text(self):
        """Test inferring Claude from text mention"""
        viewer = cursor_chronicle.CursorChatViewer()
        message = {"text": "Using Claude Sonnet for this task"}
        result = viewer.infer_model_from_context(message, 1000)
        self.assertIn("Claude", result)

    def test_infer_gpt_from_text(self):
        """Test inferring GPT from text mention"""
        viewer = cursor_chronicle.CursorChatViewer()
        message = {"text": "Using GPT-4 for this task"}
        result = viewer.infer_model_from_context(message, 1000)
        self.assertIn("GPT", result)

    def test_infer_o1_from_text(self):
        """Test inferring o1 from text mention"""
        viewer = cursor_chronicle.CursorChatViewer()
        message = {"text": "Using o1 model"}
        result = viewer.infer_model_from_context(message, 1000)
        self.assertIn("o1", result)

    def test_infer_from_medium_tokens(self):
        """Test inferring from medium token usage"""
        viewer = cursor_chronicle.CursorChatViewer()
        message = {"text": "", "is_agentic": False}
        result = viewer.infer_model_from_context(message, 50000)
        self.assertIn("high token usage", result)

    def test_infer_from_unified_mode_4(self):
        """Test inferring from unified mode 4"""
        viewer = cursor_chronicle.CursorChatViewer()
        message = {"text": "", "is_agentic": False, "unified_mode": 4}
        result = viewer.infer_model_from_context(message, 1000)
        self.assertIn("Advanced model", result)

    def test_infer_from_unified_mode_2(self):
        """Test inferring from unified mode 2"""
        viewer = cursor_chronicle.CursorChatViewer()
        message = {"text": "", "is_agentic": False, "unified_mode": 2}
        result = viewer.infer_model_from_context(message, 1000)
        self.assertIn("Standard model", result)

    def test_infer_from_many_capabilities(self):
        """Test inferring from many capabilities"""
        viewer = cursor_chronicle.CursorChatViewer()
        message = {
            "text": "",
            "is_agentic": False,
            "capabilities_ran": {f"cap{i}": True for i in range(10)},
        }
        result = viewer.infer_model_from_context(message, 1000)
        self.assertIn("complex capabilities", result)

    def test_infer_cannot_infer(self):
        """Test when cannot infer model"""
        viewer = cursor_chronicle.CursorChatViewer()
        message = {"text": "Hello", "is_agentic": False}
        result = viewer.infer_model_from_context(message, 100)
        self.assertEqual(result, "")


class TestFormatDialog(unittest.TestCase):
    """Test format_dialog method"""

    def test_format_dialog_basic(self):
        """Test basic dialog formatting"""
        viewer = cursor_chronicle.CursorChatViewer()
        messages = [
            {"type": 1, "text": "Hello", "attached_files": [], "is_thought": False},
            {"type": 2, "text": "Hi there!", "tool_data": None, "attached_files": [], "is_thought": False},
        ]
        result = viewer.format_dialog(messages, "Test Dialog", "TestProject", 1)
        self.assertIn("TestProject", result)
        self.assertIn("Test Dialog", result)
        self.assertIn("USER", result)
        self.assertIn("AI", result)

    def test_format_dialog_with_thinking(self):
        """Test dialog with thinking bubble"""
        viewer = cursor_chronicle.CursorChatViewer()
        messages = [
            {
                "type": 2,
                "text": "",
                "is_thought": True,
                "thinking_duration": 5000,
                "thinking_content": "Analyzing the problem...",
                "attached_files": [],
            }
        ]
        result = viewer.format_dialog(messages, "Test", "Project", 1)
        self.assertIn("THINKING", result)
        self.assertIn("5.0s", result)
        self.assertIn("Analyzing", result)

    def test_format_dialog_with_long_thinking_content(self):
        """Test dialog with long thinking content (truncated)"""
        viewer = cursor_chronicle.CursorChatViewer()
        long_content = "x" * 1000
        messages = [
            {
                "type": 2,
                "text": "",
                "is_thought": True,
                "thinking_duration": 1000,
                "thinking_content": long_content,
                "attached_files": [],
            }
        ]
        result = viewer.format_dialog(messages, "Test", "Project", 1)
        self.assertIn("...", result)

    def test_format_dialog_with_attached_files(self):
        """Test dialog with attached files"""
        viewer = cursor_chronicle.CursorChatViewer()
        messages = [
            {
                "type": 1,
                "text": "Check this file",
                "attached_files": [{"type": "active", "path": "/test.py"}],
                "is_thought": False,
            }
        ]
        result = viewer.format_dialog(messages, "Test", "Project", 1)
        self.assertIn("ATTACHED FILES", result)

    def test_format_dialog_with_tool_call(self):
        """Test dialog with tool call"""
        viewer = cursor_chronicle.CursorChatViewer()
        messages = [
            {
                "type": 2,
                "text": "Done",
                "tool_data": {"tool": 5, "name": "read_file", "status": "done"},
                "attached_files": [],
                "is_thought": False,
            }
        ]
        result = viewer.format_dialog(messages, "Test", "Project", 1)
        self.assertIn("TOOL", result)

    def test_format_dialog_other_type(self):
        """Test dialog with other message type"""
        viewer = cursor_chronicle.CursorChatViewer()
        messages = [
            {
                "type": 99,
                "text": "Some message",
                "tool_data": None,
                "attached_files": [],
                "is_thought": False,
            }
        ]
        result = viewer.format_dialog(messages, "Test", "Project", 1)
        self.assertIn("MESSAGE (type 99)", result)

    def test_format_dialog_other_type_with_tool(self):
        """Test dialog with other type and tool"""
        viewer = cursor_chronicle.CursorChatViewer()
        messages = [
            {
                "type": 99,
                "text": "",
                "tool_data": {"tool": 5, "name": "test", "status": "done"},
                "attached_files": [],
                "is_thought": False,
            }
        ]
        result = viewer.format_dialog(messages, "Test", "Project", 1)
        self.assertIn("MESSAGE (type 99)", result)
        self.assertIn("TOOL", result)


class TestFormatAttachedFilesAdvanced(unittest.TestCase):
    """Test format_attached_files with various file types"""

    def test_format_attached_files_with_preview(self):
        """Test active file with preview"""
        viewer = cursor_chronicle.CursorChatViewer()
        files = [
            {
                "type": "active",
                "path": "/test.py",
                "preview": "def function(): pass",
            }
        ]
        result = viewer.format_attached_files(files, 10)
        self.assertIn("Preview:", result)
        self.assertIn("def function():", result)

    def test_format_attached_files_long_preview(self):
        """Test active file with long preview (truncated)"""
        viewer = cursor_chronicle.CursorChatViewer()
        long_preview = "x" * 200
        files = [{"type": "active", "path": "/test.py", "preview": long_preview}]
        result = viewer.format_attached_files(files, 10)
        self.assertIn("...", result)

    def test_format_attached_files_selected_with_selection(self):
        """Test selected file with selection info"""
        viewer = cursor_chronicle.CursorChatViewer()
        files = [{"type": "selected", "path": "/test.py", "selection": "1-10"}]
        result = viewer.format_attached_files(files, 10)
        self.assertIn("Selection: 1-10", result)

    def test_format_attached_files_context_with_content(self):
        """Test context file with content"""
        viewer = cursor_chronicle.CursorChatViewer()
        files = [
            {
                "type": "context",
                "path": "/test.py",
                "line_range": "10-20",
                "content": "def test():",
            }
        ]
        result = viewer.format_attached_files(files, 10)
        self.assertIn("Lines: 10-20", result)
        self.assertIn("Content:", result)

    def test_format_attached_files_context_long_content(self):
        """Test context file with long content (truncated)"""
        viewer = cursor_chronicle.CursorChatViewer()
        long_content = "x" * 300
        files = [{"type": "context", "path": "/test.py", "content": long_content}]
        result = viewer.format_attached_files(files, 10)
        self.assertIn("...", result)

    def test_format_attached_files_many_project_files(self):
        """Test many project files (truncated list)"""
        viewer = cursor_chronicle.CursorChatViewer()
        files = [{"type": "project", "path": f"/file{i}.py"} for i in range(20)]
        result = viewer.format_attached_files(files, 10)
        self.assertIn("20 files", result)
        self.assertIn("and 10 more files", result)

    def test_format_attached_files_selected_context(self):
        """Test selected context files"""
        viewer = cursor_chronicle.CursorChatViewer()
        files = [
            {"type": "selected_context", "path": "/test.py", "selection": "5-15"}
        ]
        result = viewer.format_attached_files(files, 10)
        self.assertIn("Selected in context:", result)
        self.assertIn("Selection: 5-15", result)

    def test_format_attached_files_missing_path(self):
        """Test files with missing path field"""
        viewer = cursor_chronicle.CursorChatViewer()
        files = [{"type": "active"}]  # No path
        result = viewer.format_attached_files(files, 10)
        self.assertIn("unknown", result)


class TestGetDialogMessages(unittest.TestCase):
    """Test get_dialog_messages method edge cases"""

    def test_get_dialog_messages_thinking_bubble(self):
        """Test thinking bubble detection"""
        import json
        import sqlite3
        import tempfile
        from pathlib import Path
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        # Create a temporary database
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        # Add composer data
        composer_data = {
            "fullConversationHeadersOnly": [{"bubbleId": "bubble1"}]
        }
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("composerData:test123", json.dumps(composer_data)))
        
        # Add thinking bubble
        bubble_data = {
            "bubbleId": "bubble1",
            "type": 2,
            "text": "",
            "isThought": True,
            "thinkingDurationMs": 3000,
            "thinking": {"content": "Thinking about the problem..."},
        }
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("bubbleId:test123:bubble1", json.dumps(bubble_data)))
        
        conn.commit()
        conn.close()
        
        # Override the path
        viewer.global_storage_path = Path(db_path)
        
        try:
            messages = viewer.get_dialog_messages("test123")
            self.assertEqual(len(messages), 1)
            self.assertTrue(messages[0]["is_thought"])
            self.assertEqual(messages[0]["thinking_duration"], 3000)
            self.assertIn("Thinking about", messages[0]["thinking_content"])
        finally:
            os.unlink(db_path)

    def test_get_dialog_messages_thinking_string(self):
        """Test thinking as string"""
        import json
        import sqlite3
        import tempfile
        from pathlib import Path
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        composer_data = {
            "fullConversationHeadersOnly": [{"bubbleId": "bubble1"}]
        }
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("composerData:test123", json.dumps(composer_data)))
        
        # Make value > 100 chars to pass LENGTH(value) > 100 filter
        bubble_data = {
            "bubbleId": "bubble1",
            "type": 2,
            "text": "",
            "thinking": "Direct thinking string" + " " * 100,
        }
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("bubbleId:test123:bubble1", json.dumps(bubble_data)))
        
        conn.commit()
        conn.close()
        
        viewer.global_storage_path = Path(db_path)
        
        try:
            messages = viewer.get_dialog_messages("test123")
            self.assertEqual(len(messages), 1)
            self.assertTrue(messages[0]["is_thought"])
            self.assertIn("Direct thinking string", messages[0]["thinking_content"])
        finally:
            os.unlink(db_path)


class TestMainFunction(unittest.TestCase):
    """Test main function and CLI parsing"""

    def test_parse_date_slash_format(self):
        """Test parsing date with slash format"""
        from cursor_chronicle import parse_date
        
        result = parse_date("15/06/2024")
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)

    def test_parse_date_with_seconds(self):
        """Test parsing date with full time"""
        from cursor_chronicle import parse_date
        
        result = parse_date("2024-06-15 14:30:45")
        self.assertEqual(result.second, 45)


class TestListAllDialogsDisplay(unittest.TestCase):
    """Test list_all_dialogs display output"""

    def test_list_all_dialogs_no_dialogs(self):
        """Test list_all_dialogs with no dialogs"""
        from datetime import datetime
        from io import StringIO
        import sys
        
        viewer = cursor_chronicle.CursorChatViewer()
        # Use far future dates to ensure no dialogs
        start_date = datetime(2099, 1, 1)
        end_date = datetime(2099, 12, 31)
        
        captured = StringIO()
        sys.stdout = captured
        try:
            viewer.list_all_dialogs(start_date=start_date, end_date=end_date)
        finally:
            sys.stdout = sys.__stdout__
        
        output = captured.getvalue()
        self.assertIn("No dialogs found", output)

    def test_list_all_dialogs_no_dialogs_start_only(self):
        """Test list_all_dialogs with only start date filter"""
        from datetime import datetime
        from io import StringIO
        import sys
        
        viewer = cursor_chronicle.CursorChatViewer()
        start_date = datetime(2099, 1, 1)
        
        captured = StringIO()
        sys.stdout = captured
        try:
            viewer.list_all_dialogs(start_date=start_date)
        finally:
            sys.stdout = sys.__stdout__
        
        output = captured.getvalue()
        self.assertIn("No dialogs found", output)
        self.assertIn("after", output)

    def test_list_all_dialogs_no_dialogs_end_only(self):
        """Test list_all_dialogs with only end date filter"""
        from datetime import datetime
        from io import StringIO
        import sys
        
        viewer = cursor_chronicle.CursorChatViewer()
        end_date = datetime(1990, 1, 1)
        
        captured = StringIO()
        sys.stdout = captured
        try:
            viewer.list_all_dialogs(end_date=end_date)
        finally:
            sys.stdout = sys.__stdout__
        
        output = captured.getvalue()
        self.assertIn("No dialogs found", output)
        self.assertIn("before", output)


class TestShowStatistics(unittest.TestCase):
    """Test show_statistics method output"""

    def test_show_statistics_output(self):
        """Test show_statistics produces output"""
        from datetime import datetime, timedelta
        from io import StringIO
        import sys
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        # Use short date range to speed up
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        captured = StringIO()
        sys.stdout = captured
        try:
            viewer.show_statistics(
                days=1,
                start_date=start_date,
                end_date=end_date
            )
        finally:
            sys.stdout = sys.__stdout__
        
        output = captured.getvalue()
        # Should contain statistics header
        self.assertIn("Collecting statistics", output)


class TestFormatStatisticsEdgeCases(unittest.TestCase):
    """Test format_statistics edge cases"""

    def test_format_statistics_no_tokens(self):
        """Test formatting stats without tokens"""
        from collections import Counter
        from datetime import datetime
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        stats = {
            "period_start": datetime(2024, 1, 1),
            "period_end": datetime(2024, 1, 31),
            "total_dialogs": 5,
            "total_messages": 100,
            "user_messages": 30,
            "ai_messages": 70,
            "tool_calls": 0,
            "thinking_bubbles": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_thinking_time_ms": 0,
            "projects": {},
            "tool_usage": Counter(),
            "daily_activity": {},
            "dialogs_by_length": [],
        }
        
        result = viewer.format_statistics(stats)
        self.assertIn("Total dialogs:", result)
        # Should not contain TOKEN section when no tokens
        self.assertNotIn("TOKEN USAGE", result)

    def test_format_statistics_max_days_limit(self):
        """Test daily activity is limited by max_days"""
        from collections import Counter
        from datetime import datetime
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        # Create many daily activity entries
        daily_activity = {f"2024-01-{i:02d}": {"dialogs": 1, "messages": 5} for i in range(1, 25)}
        
        stats = {
            "period_start": datetime(2024, 1, 1),
            "period_end": datetime(2024, 1, 31),
            "total_dialogs": 20,
            "total_messages": 100,
            "user_messages": 30,
            "ai_messages": 70,
            "tool_calls": 0,
            "thinking_bubbles": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_thinking_time_ms": 0,
            "projects": {},
            "tool_usage": Counter(),
            "daily_activity": daily_activity,
            "dialogs_by_length": [],
        }
        
        result = viewer.format_statistics(stats, max_days=5)
        self.assertIn("DAILY ACTIVITY", result)
        self.assertIn("more days", result)

    def test_format_statistics_many_projects(self):
        """Test project activity truncation"""
        from collections import Counter
        from datetime import datetime
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        # Create many projects
        projects = {
            f"project{i}": {
                "dialogs": i,
                "messages": i * 10,
                "user_messages": i * 3,
                "ai_messages": i * 7,
                "tool_calls": i,
                "tokens_in": i * 100,
                "tokens_out": i * 50,
                "dialog_names": [],
            }
            for i in range(1, 20)
        }
        
        stats = {
            "period_start": datetime(2024, 1, 1),
            "period_end": datetime(2024, 1, 31),
            "total_dialogs": 100,
            "total_messages": 1000,
            "user_messages": 300,
            "ai_messages": 700,
            "tool_calls": 50,
            "thinking_bubbles": 0,
            "total_tokens_in": 10000,
            "total_tokens_out": 5000,
            "total_thinking_time_ms": 0,
            "projects": projects,
            "tool_usage": Counter(),
            "daily_activity": {},
            "dialogs_by_length": [],
        }
        
        result = viewer.format_statistics(stats, top_n=5)
        self.assertIn("PROJECT ACTIVITY", result)
        self.assertIn("more projects", result)


class TestThinkingBubbleBase64(unittest.TestCase):
    """Test thinking bubble with base64 encoded content"""

    def test_thinking_bubble_base64_signature(self):
        """Test thinking bubble with base64-like signature is handled"""
        import json
        import sqlite3
        import tempfile
        from pathlib import Path
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        composer_data = {
            "fullConversationHeadersOnly": [{"bubbleId": "bubble1"}],
            "padding": "x" * 100,
        }
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("composerData:test123", json.dumps(composer_data)))
        
        # Bubble with base64-like signature (starts with AVSoXO)
        bubble_data = {
            "bubbleId": "bubble1",
            "type": 2,
            "text": "",
            "isThought": True,
            "thinking": {"signature": "AVSoXOInvalidBase64Data" + "x" * 100},
        }
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("bubbleId:test123:bubble1", json.dumps(bubble_data)))
        
        conn.commit()
        conn.close()
        
        viewer.global_storage_path = Path(db_path)
        
        try:
            messages = viewer.get_dialog_messages("test123")
            self.assertEqual(len(messages), 1)
            self.assertTrue(messages[0]["is_thought"])
        finally:
            os.unlink(db_path)


class TestGetDialogMessagesNoOrdered(unittest.TestCase):
    """Test get_dialog_messages fallback to rowid order"""

    def test_get_dialog_messages_no_full_conversation(self):
        """Test when no fullConversationHeadersOnly exists"""
        import json
        import sqlite3
        import tempfile
        from pathlib import Path
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        # Composer data WITHOUT fullConversationHeadersOnly
        composer_data = {"padding": "x" * 100}
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("composerData:test123", json.dumps(composer_data)))
        
        # Add bubbles
        bubble_data = {
            "bubbleId": "bubble1",
            "type": 1,
            "text": "Hello " + "x" * 100,
        }
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("bubbleId:test123:bubble1", json.dumps(bubble_data)))
        
        conn.commit()
        conn.close()
        
        viewer.global_storage_path = Path(db_path)
        
        try:
            messages = viewer.get_dialog_messages("test123")
            self.assertEqual(len(messages), 1)
        finally:
            os.unlink(db_path)

    def test_get_dialog_messages_json_decode_error(self):
        """Test handling of JSON decode error in bubble"""
        import json
        import sqlite3
        import tempfile
        from pathlib import Path
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE cursorDiskKV (key TEXT, value TEXT)''')
        
        # Add invalid JSON bubble (> 100 chars)
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                      ("bubbleId:test123:bubble1", "invalid json " + "x" * 100))
        
        conn.commit()
        conn.close()
        
        viewer.global_storage_path = Path(db_path)
        
        try:
            messages = viewer.get_dialog_messages("test123")
            # Should return empty due to JSON error
            self.assertEqual(len(messages), 0)
        finally:
            os.unlink(db_path)


if __name__ == "__main__":
    unittest.main()
