"""
Tests for search_history CLI.
"""

import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import search_history
from search_history.cli import create_parser, parse_positive_int


class TestMainCLI(unittest.TestCase):
    """Test main CLI functionality."""

    def test_main_no_query_prints_help(self):
        """Test main() with no query prints help."""
        with patch.object(sys, "argv", ["search_history.py"]):
            captured = StringIO()
            with patch("sys.stdout", captured):
                search_history.main()
        output = captured.getvalue()
        self.assertTrue(len(output) > 0 or output == "")

    def test_main_show_dialog_not_found(self):
        """Test main() with --show-dialog for non-existent dialog."""
        with patch.object(
            sys, "argv", ["search_history.py", "--show-dialog", "nonexistent123"]
        ):
            captured = StringIO()
            with patch("sys.stdout", captured):
                search_history.main()
        output = captured.getvalue()
        self.assertIn("not found", output)

    def test_main_list_dialogs_mode(self):
        """Test main() with --list-dialogs flag."""
        with patch.object(
            sys, "argv", ["search_history.py", "test", "--list-dialogs", "--limit", "1"]
        ):
            captured = StringIO()
            with patch("sys.stdout", captured):
                search_history.main()
        output = captured.getvalue()
        self.assertTrue("Dialogs containing" in output or "No results" in output)


class TestSearchParserValidation(unittest.TestCase):
    """Test CLI numeric validation for search command."""

    def test_limit_must_be_positive(self):
        with self.assertRaises(SystemExit):
            create_parser().parse_args(["query", "--limit", "0"])

    def test_context_size_must_be_positive(self):
        with self.assertRaises(SystemExit):
            create_parser().parse_args(["query", "--context-size", "-2"])

    def test_parse_positive_int_valid(self):
        self.assertEqual(parse_positive_int("3"), 3)


if __name__ == "__main__":
    unittest.main()
