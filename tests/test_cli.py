"""
Tests for cli.py module - command-line interface.
"""

import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cursor_chronicle


class TestParseDateFunction(unittest.TestCase):
    """Test the parse_date helper function."""

    def test_parse_date_iso_format(self):
        """Test parsing ISO date format."""
        result = cursor_chronicle.parse_date("2024-06-15")
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)

    def test_parse_date_with_time(self):
        """Test parsing date with time."""
        result = cursor_chronicle.parse_date("2024-06-15 14:30")
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.minute, 30)

    def test_parse_date_european_format(self):
        """Test parsing European date format."""
        result = cursor_chronicle.parse_date("15.06.2024")
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)

    def test_parse_date_invalid_raises(self):
        """Test that invalid date raises ArgumentTypeError."""
        with self.assertRaises(argparse.ArgumentTypeError):
            cursor_chronicle.parse_date("invalid-date")

    def test_parse_date_slash_format(self):
        """Test parsing date with slash format."""
        result = cursor_chronicle.parse_date("15/06/2024")
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)

    def test_parse_date_with_seconds(self):
        """Test parsing date with full time."""
        result = cursor_chronicle.parse_date("2024-06-15 14:30:45")
        self.assertEqual(result.second, 45)


class TestMainFunction(unittest.TestCase):
    """Test main function and CLI behavior."""

    def test_main_function_exists(self):
        """Test that main function exists."""
        self.assertTrue(hasattr(cursor_chronicle, "main"))
        self.assertTrue(callable(cursor_chronicle.main))


if __name__ == "__main__":
    unittest.main()
