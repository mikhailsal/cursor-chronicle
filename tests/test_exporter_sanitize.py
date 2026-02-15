"""
Tests for exporter.py module - Sanitization and path building functions.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cursor_chronicle.exporter import (
    build_folder_path,
    build_md_filename,
    sanitize_filename,
    sanitize_project_name,
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


if __name__ == "__main__":
    unittest.main()
