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


if __name__ == "__main__":
    unittest.main()
