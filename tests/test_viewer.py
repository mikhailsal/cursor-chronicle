"""
Tests for viewer.py module - core CursorChatViewer functionality.
"""

import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cursor_chronicle


class TestCursorChronicle(unittest.TestCase):
    """Test basic functionality of cursor_chronicle."""

    def test_import(self):
        """Test that cursor_chronicle can be imported."""
        self.assertIsNotNone(cursor_chronicle)

    def test_cursor_chat_viewer_class(self):
        """Test that CursorChatViewer class exists and can be instantiated."""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertIsNotNone(viewer)

    def test_tool_types_mapping(self):
        """Test that tool types mapping is properly defined."""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertIsInstance(viewer.tool_types, dict)
        self.assertGreater(len(viewer.tool_types), 0)
        self.assertIn(1, viewer.tool_types)
        self.assertIn(15, viewer.tool_types)

    def test_config_paths(self):
        """Test that config paths are properly set."""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertIsInstance(viewer.cursor_config_path, Path)
        self.assertIsInstance(viewer.workspace_storage_path, Path)
        self.assertIsInstance(viewer.global_storage_path, Path)
        self.assertTrue(str(viewer.cursor_config_path).endswith(".config/Cursor/User"))
        self.assertTrue(str(viewer.workspace_storage_path).endswith("workspaceStorage"))
        self.assertTrue(str(viewer.global_storage_path).endswith("state.vscdb"))


class TestListAllDialogs(unittest.TestCase):
    """Test list_all_dialogs and get_all_dialogs functionality."""

    def test_get_all_dialogs_method_exists(self):
        """Test that get_all_dialogs method exists."""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertTrue(hasattr(viewer, "get_all_dialogs"))
        self.assertTrue(callable(viewer.get_all_dialogs))

    def test_list_all_dialogs_method_exists(self):
        """Test that list_all_dialogs method exists."""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertTrue(hasattr(viewer, "list_all_dialogs"))
        self.assertTrue(callable(viewer.list_all_dialogs))

    def test_get_all_dialogs_returns_list(self):
        """Test that get_all_dialogs returns a list."""
        viewer = cursor_chronicle.CursorChatViewer()
        result = viewer.get_all_dialogs()
        self.assertIsInstance(result, list)

    def test_get_all_dialogs_with_date_filtering(self):
        """Test date filtering parameters."""
        viewer = cursor_chronicle.CursorChatViewer()
        start = datetime(2024, 1, 1)
        result = viewer.get_all_dialogs(start_date=start)
        self.assertIsInstance(result, list)
        for dialog in result:
            if dialog.get("last_updated"):
                dialog_date = datetime.fromtimestamp(dialog["last_updated"] / 1000)
                self.assertGreaterEqual(dialog_date, start)

    def test_get_all_dialogs_with_end_date(self):
        """Test end date filtering."""
        viewer = cursor_chronicle.CursorChatViewer()
        end = datetime(2030, 12, 31)
        result = viewer.get_all_dialogs(end_date=end)
        self.assertIsInstance(result, list)
        for dialog in result:
            if dialog.get("last_updated"):
                dialog_date = datetime.fromtimestamp(dialog["last_updated"] / 1000)
                self.assertLessEqual(dialog_date, end)

    def test_get_all_dialogs_with_project_filter(self):
        """Test project name filtering."""
        viewer = cursor_chronicle.CursorChatViewer()
        all_dialogs = viewer.get_all_dialogs()
        if all_dialogs:
            project_name = all_dialogs[0].get("project_name", "")
            if project_name:
                filtered = viewer.get_all_dialogs(project_filter=project_name)
                for dialog in filtered:
                    self.assertIn(project_name.lower(), dialog["project_name"].lower())

    def test_get_all_dialogs_date_range(self):
        """Test date range filtering."""
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
        """Test ascending sort by created_at (default)."""
        viewer = cursor_chronicle.CursorChatViewer()
        dialogs = viewer.get_all_dialogs()
        if len(dialogs) > 1:
            for i in range(len(dialogs) - 1):
                current = dialogs[i].get("created_at", 0)
                next_one = dialogs[i + 1].get("created_at", 0)
                self.assertLessEqual(current, next_one)

    def test_get_all_dialogs_sorted_by_created_desc(self):
        """Test descending sort by created_at."""
        viewer = cursor_chronicle.CursorChatViewer()
        dialogs = viewer.get_all_dialogs(sort_desc=True)
        if len(dialogs) > 1:
            for i in range(len(dialogs) - 1):
                current = dialogs[i].get("created_at", 0)
                next_one = dialogs[i + 1].get("created_at", 0)
                self.assertGreaterEqual(current, next_one)

    def test_get_all_dialogs_sorted_by_updated_asc(self):
        """Test ascending sort by last_updated."""
        viewer = cursor_chronicle.CursorChatViewer()
        dialogs = viewer.get_all_dialogs(use_updated=True)
        if len(dialogs) > 1:
            for i in range(len(dialogs) - 1):
                current = dialogs[i].get("last_updated", 0)
                next_one = dialogs[i + 1].get("last_updated", 0)
                self.assertLessEqual(current, next_one)

    def test_get_all_dialogs_sorted_by_updated_desc(self):
        """Test descending sort by last_updated."""
        viewer = cursor_chronicle.CursorChatViewer()
        dialogs = viewer.get_all_dialogs(use_updated=True, sort_desc=True)
        if len(dialogs) > 1:
            for i in range(len(dialogs) - 1):
                current = dialogs[i].get("last_updated", 0)
                next_one = dialogs[i + 1].get("last_updated", 0)
                self.assertGreaterEqual(current, next_one)

    def test_get_all_dialogs_sorted_by_name(self):
        """Test sorting by dialog name."""
        viewer = cursor_chronicle.CursorChatViewer()
        dialogs = viewer.get_all_dialogs(sort_by="name")
        if len(dialogs) > 1:
            for i in range(len(dialogs) - 1):
                current = dialogs[i].get("name", "").lower()
                next_one = dialogs[i + 1].get("name", "").lower()
                self.assertLessEqual(current, next_one)

    def test_get_all_dialogs_sorted_by_project(self):
        """Test sorting by project name."""
        viewer = cursor_chronicle.CursorChatViewer()
        dialogs = viewer.get_all_dialogs(sort_by="project")
        if len(dialogs) > 1:
            for i in range(len(dialogs) - 1):
                current = dialogs[i].get("project_name", "").lower()
                next_one = dialogs[i + 1].get("project_name", "").lower()
                self.assertLessEqual(current, next_one)

    def test_dialog_dict_structure(self):
        """Test that returned dialog dicts have expected keys."""
        viewer = cursor_chronicle.CursorChatViewer()
        dialogs = viewer.get_all_dialogs()
        expected_keys = ["composer_id", "name", "project_name", "folder_path", "last_updated", "created_at"]
        for dialog in dialogs:
            for key in expected_keys:
                self.assertIn(key, dialog)


class TestListAllDialogsDisplay(unittest.TestCase):
    """Test list_all_dialogs display output."""

    def test_list_all_dialogs_no_dialogs(self):
        """Test list_all_dialogs with no dialogs."""
        from io import StringIO
        import sys as sys_module
        
        viewer = cursor_chronicle.CursorChatViewer()
        start_date = datetime(2099, 1, 1)
        end_date = datetime(2099, 12, 31)
        
        captured = StringIO()
        sys_module.stdout = captured
        try:
            viewer.list_all_dialogs(start_date=start_date, end_date=end_date)
        finally:
            sys_module.stdout = sys_module.__stdout__
        
        output = captured.getvalue()
        self.assertIn("No dialogs found", output)

    def test_list_all_dialogs_no_dialogs_start_only(self):
        """Test list_all_dialogs with only start date filter."""
        from io import StringIO
        import sys as sys_module
        
        viewer = cursor_chronicle.CursorChatViewer()
        start_date = datetime(2099, 1, 1)
        
        captured = StringIO()
        sys_module.stdout = captured
        try:
            viewer.list_all_dialogs(start_date=start_date)
        finally:
            sys_module.stdout = sys_module.__stdout__
        
        output = captured.getvalue()
        self.assertIn("No dialogs found", output)
        self.assertIn("after", output)

    def test_list_all_dialogs_no_dialogs_end_only(self):
        """Test list_all_dialogs with only end date filter."""
        from io import StringIO
        import sys as sys_module
        
        viewer = cursor_chronicle.CursorChatViewer()
        end_date = datetime(1990, 1, 1)
        
        captured = StringIO()
        sys_module.stdout = captured
        try:
            viewer.list_all_dialogs(end_date=end_date)
        finally:
            sys_module.stdout = sys_module.__stdout__
        
        output = captured.getvalue()
        self.assertIn("No dialogs found", output)
        self.assertIn("before", output)


class TestListAllDialogsWithData(unittest.TestCase):
    """Test list_all_dialogs with actual data."""

    def test_list_all_dialogs_with_limit(self):
        """Test list_all_dialogs respects limit."""
        from io import StringIO
        import sys as sys_module
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        captured = StringIO()
        sys_module.stdout = captured
        try:
            viewer.list_all_dialogs(limit=2)
        finally:
            sys_module.stdout = sys_module.__stdout__
        
        output = captured.getvalue()
        # Should either have "more dialogs" or show limited results
        if "All dialogs" in output:
            # Has dialogs, check limit works
            dialog_count = output.count("💬")
            self.assertLessEqual(dialog_count, 2)

    def test_list_all_dialogs_with_project_filter(self):
        """Test list_all_dialogs with project filter."""
        from io import StringIO
        import sys as sys_module
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        captured = StringIO()
        sys_module.stdout = captured
        try:
            viewer.list_all_dialogs(project_filter="cursor-chronicle", limit=5)
        finally:
            sys_module.stdout = sys_module.__stdout__
        
        output = captured.getvalue()
        # Should show filtered results or no dialogs
        self.assertTrue(
            "cursor-chronicle" in output.lower() or "No dialogs found" in output
        )


class TestListProjects(unittest.TestCase):
    """Test list_projects method."""

    def test_list_projects_output(self):
        """Test list_projects produces output."""
        from io import StringIO
        import sys as sys_module
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        captured = StringIO()
        sys_module.stdout = captured
        try:
            viewer.list_projects()
        finally:
            sys_module.stdout = sys_module.__stdout__
        
        output = captured.getvalue()
        # Should have "Available projects" or "No projects found"
        self.assertTrue(
            "Available projects" in output or "No projects found" in output
        )


class TestListDialogs(unittest.TestCase):
    """Test list_dialogs method."""

    def test_list_dialogs_project_not_found(self):
        """Test list_dialogs with nonexistent project."""
        from io import StringIO
        import sys as sys_module
        
        viewer = cursor_chronicle.CursorChatViewer()
        
        captured = StringIO()
        sys_module.stdout = captured
        try:
            viewer.list_dialogs("nonexistent-project-xyz-12345")
        finally:
            sys_module.stdout = sys_module.__stdout__
        
        output = captured.getvalue()
        self.assertIn("not found", output)

    def test_list_dialogs_with_valid_project(self):
        """Test list_dialogs with a valid project."""
        from io import StringIO
        import sys as sys_module
        
        viewer = cursor_chronicle.CursorChatViewer()
        projects = viewer.get_projects()
        
        if projects:
            project_name = projects[0]["project_name"]
            
            captured = StringIO()
            sys_module.stdout = captured
            try:
                viewer.list_dialogs(project_name)
            finally:
                sys_module.stdout = sys_module.__stdout__
            
            output = captured.getvalue()
            # Should show dialogs or "No dialogs found"
            self.assertTrue(
                "Dialogs in project" in output or "No dialogs found" in output
            )


class TestViewerMethods(unittest.TestCase):
    """Test various viewer methods."""

    def test_get_dialog_messages_method_exists(self):
        """Test that get_dialog_messages method exists."""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertTrue(hasattr(viewer, "get_dialog_messages"))

    def test_format_attached_files_method_exists(self):
        """Test that format_attached_files method exists."""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertTrue(hasattr(viewer, "format_attached_files"))
        result = viewer.format_attached_files([], 1)
        self.assertEqual(result, "")

    def test_format_tool_call_method_exists(self):
        """Test that format_tool_call method exists."""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertTrue(hasattr(viewer, "format_tool_call"))
        result = viewer.format_tool_call({}, 1)
        self.assertEqual(result, "")

    def test_format_token_info_method_exists(self):
        """Test that format_token_info method exists."""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertTrue(hasattr(viewer, "format_token_info"))
        result = viewer.format_token_info({})
        self.assertEqual(result, "")

    def test_infer_model_from_context_method_exists(self):
        """Test that infer_model_from_context method exists."""
        viewer = cursor_chronicle.CursorChatViewer()
        self.assertTrue(hasattr(viewer, "infer_model_from_context"))
        result = viewer.infer_model_from_context({}, 100)
        self.assertIsInstance(result, str)


if __name__ == "__main__":
    unittest.main()
