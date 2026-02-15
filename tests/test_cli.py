"""
Tests for cli.py module - command-line interface.
"""

import argparse
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import cursor_chronicle
from cursor_chronicle.cli import (
    _run_export,
    _show_config,
    create_parser,
    show_dialog,
)


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


class TestCreateParser(unittest.TestCase):
    """Test argument parser creation."""

    def test_create_parser_returns_parser(self):
        """Test that create_parser returns an ArgumentParser."""
        parser = create_parser()
        self.assertIsInstance(parser, argparse.ArgumentParser)

    def test_parser_has_export_args(self):
        """Test that parser has export-related arguments."""
        parser = create_parser()
        args = parser.parse_args(["--export"])
        self.assertTrue(args.export)

    def test_parser_has_verbosity_arg(self):
        """Test that parser has verbosity argument."""
        parser = create_parser()
        args = parser.parse_args(["--verbosity", "3"])
        self.assertEqual(args.verbosity, 3)

    def test_parser_has_export_path_arg(self):
        """Test that parser has export-path argument."""
        parser = create_parser()
        args = parser.parse_args(["--export-path", "/tmp/test"])
        self.assertEqual(args.export_path, "/tmp/test")

    def test_parser_has_show_config_arg(self):
        """Test that parser has show-config argument."""
        parser = create_parser()
        args = parser.parse_args(["--show-config"])
        self.assertTrue(args.show_config)

    def test_parser_has_stats_arg(self):
        """Test that parser has stats argument."""
        parser = create_parser()
        args = parser.parse_args(["--stats"])
        self.assertTrue(args.stats)

    def test_parser_has_list_all_arg(self):
        """Test that parser has list-all argument."""
        parser = create_parser()
        args = parser.parse_args(["--list-all"])
        self.assertTrue(args.list_all)

    def test_parser_default_values(self):
        """Test parser default values."""
        parser = create_parser()
        args = parser.parse_args([])
        self.assertEqual(args.limit, 50)
        self.assertEqual(args.days, 30)
        self.assertEqual(args.top, 10)
        self.assertEqual(args.max_output_lines, 1)
        self.assertFalse(args.desc)
        self.assertFalse(args.updated)


class TestShowConfig(unittest.TestCase):
    """Test _show_config function."""

    @patch("cursor_chronicle.cli.ensure_config_exists")
    def test_show_config_output(self, mock_ensure):
        """Test that show_config displays configuration."""
        mock_ensure.return_value = {
            "export_path": "/test/path",
            "verbosity": 2,
        }
        
        captured = StringIO()
        sys.stdout = captured
        try:
            _show_config()
        finally:
            sys.stdout = sys.__stdout__
        
        output = captured.getvalue()
        self.assertIn("configuration", output.lower())
        self.assertIn("/test/path", output)
        self.assertIn("standard", output)


class TestRunExport(unittest.TestCase):
    """Test _run_export function."""

    @patch("cursor_chronicle.cli.export_dialogs")
    @patch("cursor_chronicle.cli.show_export_summary")
    def test_run_export_calls_export_dialogs(self, mock_summary, mock_export):
        """Test that _run_export calls export_dialogs."""
        mock_export.return_value = {
            "total_dialogs": 5,
            "exported": 5,
            "errors": 0,
            "skipped": 0,
            "export_path": "/tmp/test",
            "verbosity": 2,
        }
        mock_summary.return_value = "Summary"
        
        args = MagicMock()
        args.export_path = None
        args.verbosity = None
        args.project = None
        args.start_date = None
        args.end_date = None
        
        viewer = MagicMock()
        
        captured = StringIO()
        sys.stdout = captured
        try:
            _run_export(args, viewer)
        finally:
            sys.stdout = sys.__stdout__
        
        mock_export.assert_called_once()

    @patch("cursor_chronicle.cli.export_dialogs")
    @patch("cursor_chronicle.cli.show_export_summary")
    def test_run_export_with_custom_path(self, mock_summary, mock_export):
        """Test that _run_export uses custom export path."""
        mock_export.return_value = {
            "total_dialogs": 1,
            "exported": 1,
            "errors": 0,
            "skipped": 0,
            "export_path": "/custom/path",
            "verbosity": 3,
        }
        mock_summary.return_value = "Summary"
        
        args = MagicMock()
        args.export_path = "/custom/path"
        args.verbosity = 3
        args.project = "myproject"
        args.start_date = None
        args.end_date = None
        
        viewer = MagicMock()
        
        captured = StringIO()
        sys.stdout = captured
        try:
            _run_export(args, viewer)
        finally:
            sys.stdout = sys.__stdout__
        
        call_kwargs = mock_export.call_args[1]
        self.assertEqual(call_kwargs["export_path"], Path("/custom/path"))
        self.assertEqual(call_kwargs["verbosity"], 3)
        self.assertEqual(call_kwargs["project_filter"], "myproject")


class TestShowDialog(unittest.TestCase):
    """Test show_dialog function."""

    def test_show_dialog_no_projects(self):
        """Test show_dialog when no projects found."""
        viewer = MagicMock()
        viewer.get_projects.return_value = []
        
        captured = StringIO()
        sys.stdout = captured
        try:
            show_dialog(viewer)
        finally:
            sys.stdout = sys.__stdout__
        
        output = captured.getvalue()
        self.assertIn("No projects found", output)

    def test_show_dialog_project_not_found(self):
        """Test show_dialog when specific project not found."""
        viewer = MagicMock()
        viewer.get_projects.return_value = [
            {"project_name": "other-project", "composers": []}
        ]
        
        captured = StringIO()
        sys.stdout = captured
        try:
            show_dialog(viewer, project_name="nonexistent")
        finally:
            sys.stdout = sys.__stdout__
        
        output = captured.getvalue()
        self.assertIn("not found", output)

    def test_show_dialog_dialog_not_found(self):
        """Test show_dialog when specific dialog not found."""
        viewer = MagicMock()
        viewer.get_projects.return_value = [
            {
                "project_name": "test-project",
                "composers": [{"name": "other-dialog", "composerId": "123"}],
            }
        ]
        
        captured = StringIO()
        sys.stdout = captured
        try:
            show_dialog(viewer, project_name="test-project", dialog_name="nonexistent")
        finally:
            sys.stdout = sys.__stdout__
        
        output = captured.getvalue()
        self.assertIn("not found", output)

    def test_show_dialog_no_composers(self):
        """Test show_dialog when project has no dialogs."""
        viewer = MagicMock()
        viewer.get_projects.return_value = [
            {"project_name": "empty-project", "composers": []}
        ]
        
        captured = StringIO()
        sys.stdout = captured
        try:
            show_dialog(viewer, project_name="empty-project")
        finally:
            sys.stdout = sys.__stdout__
        
        output = captured.getvalue()
        self.assertIn("No dialogs found", output)

    def test_show_dialog_no_composer_id(self):
        """Test show_dialog when composer has no ID."""
        viewer = MagicMock()
        viewer.get_projects.return_value = [
            {
                "project_name": "test-project",
                "composers": [{"name": "test-dialog", "lastUpdatedAt": 1000}],
            }
        ]
        
        captured = StringIO()
        sys.stdout = captured
        try:
            show_dialog(viewer, project_name="test-project")
        finally:
            sys.stdout = sys.__stdout__
        
        output = captured.getvalue()
        self.assertIn("ID not found", output)

    @patch("cursor_chronicle.cli.get_dialog_messages")
    def test_show_dialog_no_messages(self, mock_get_messages):
        """Test show_dialog when dialog has no messages."""
        mock_get_messages.return_value = []
        
        viewer = MagicMock()
        viewer.get_projects.return_value = [
            {
                "project_name": "test-project",
                "composers": [
                    {"name": "test-dialog", "composerId": "abc123", "lastUpdatedAt": 1000}
                ],
            }
        ]
        
        captured = StringIO()
        sys.stdout = captured
        try:
            show_dialog(viewer, project_name="test-project")
        finally:
            sys.stdout = sys.__stdout__
        
        output = captured.getvalue()
        self.assertIn("No messages found", output)

    @patch("cursor_chronicle.cli.get_dialog_messages")
    def test_show_dialog_error_handling(self, mock_get_messages):
        """Test show_dialog error handling."""
        mock_get_messages.side_effect = Exception("Database error")
        
        viewer = MagicMock()
        viewer.get_projects.return_value = [
            {
                "project_name": "test-project",
                "composers": [
                    {"name": "test-dialog", "composerId": "abc123", "lastUpdatedAt": 1000}
                ],
            }
        ]
        
        captured = StringIO()
        sys.stdout = captured
        try:
            show_dialog(viewer, project_name="test-project")
        finally:
            sys.stdout = sys.__stdout__
        
        output = captured.getvalue()
        self.assertIn("Error reading dialog", output)

    @patch("cursor_chronicle.cli.get_dialog_messages")
    @patch("cursor_chronicle.cli.format_dialog")
    def test_show_dialog_success(self, mock_format, mock_get_messages):
        """Test show_dialog successful output."""
        mock_get_messages.return_value = [{"type": 1, "text": "Hello"}]
        mock_format.return_value = "Formatted dialog output"
        
        viewer = MagicMock()
        viewer.get_projects.return_value = [
            {
                "project_name": "test-project",
                "composers": [
                    {"name": "test-dialog", "composerId": "abc123", "lastUpdatedAt": 1000}
                ],
            }
        ]
        
        captured = StringIO()
        sys.stdout = captured
        try:
            show_dialog(viewer, project_name="test-project")
        finally:
            sys.stdout = sys.__stdout__
        
        output = captured.getvalue()
        self.assertIn("Formatted dialog output", output)

    @patch("cursor_chronicle.cli.get_dialog_messages")
    @patch("cursor_chronicle.cli.format_dialog")
    def test_show_dialog_finds_by_partial_name(self, mock_format, mock_get_messages):
        """Test show_dialog finds dialog by partial name match."""
        mock_get_messages.return_value = [{"type": 1, "text": "Hello"}]
        mock_format.return_value = "Output"
        
        viewer = MagicMock()
        viewer.get_projects.return_value = [
            {
                "project_name": "test-project",
                "composers": [
                    {"name": "My Long Dialog Name", "composerId": "abc", "lastUpdatedAt": 1000}
                ],
            }
        ]
        
        captured = StringIO()
        sys.stdout = captured
        try:
            show_dialog(viewer, project_name="test", dialog_name="long dialog")
        finally:
            sys.stdout = sys.__stdout__
        
        mock_get_messages.assert_called_once()


if __name__ == "__main__":
    unittest.main()
