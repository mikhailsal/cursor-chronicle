"""Tests for cli.py module - command-line interface."""

import argparse
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import cursor_chronicle
from cursor_chronicle.cli import _run_export, _show_config, create_parser, show_dialog


class TestParseDateFunction(unittest.TestCase):
    """Test the parse_date helper function."""

    def test_iso_format(self):
        result = cursor_chronicle.parse_date("2024-06-15")
        self.assertEqual((result.year, result.month, result.day), (2024, 6, 15))

    def test_with_time(self):
        result = cursor_chronicle.parse_date("2024-06-15 14:30")
        self.assertEqual((result.hour, result.minute), (14, 30))

    def test_european_format(self):
        result = cursor_chronicle.parse_date("15.06.2024")
        self.assertEqual((result.year, result.month, result.day), (2024, 6, 15))

    def test_invalid_raises(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            cursor_chronicle.parse_date("invalid-date")

    def test_slash_format(self):
        result = cursor_chronicle.parse_date("15/06/2024")
        self.assertEqual((result.year, result.month, result.day), (2024, 6, 15))

    def test_with_seconds(self):
        result = cursor_chronicle.parse_date("2024-06-15 14:30:45")
        self.assertEqual(result.second, 45)


class TestMainFunction(unittest.TestCase):
    """Test main function and CLI behavior."""

    def test_main_function_exists(self):
        self.assertTrue(hasattr(cursor_chronicle, "main"))
        self.assertTrue(callable(cursor_chronicle.main))


class TestCreateParser(unittest.TestCase):
    """Test argument parser creation."""

    def test_returns_parser(self):
        self.assertIsInstance(create_parser(), argparse.ArgumentParser)

    def test_export_args(self):
        self.assertTrue(create_parser().parse_args(["--export"]).export)

    def test_verbosity_arg(self):
        self.assertEqual(create_parser().parse_args(["--verbosity", "3"]).verbosity, 3)

    def test_export_path_arg(self):
        self.assertEqual(create_parser().parse_args(["--export-path", "/tmp/test"]).export_path, "/tmp/test")

    def test_show_config_arg(self):
        self.assertTrue(create_parser().parse_args(["--show-config"]).show_config)

    def test_stats_arg(self):
        self.assertTrue(create_parser().parse_args(["--stats"]).stats)

    def test_list_all_arg(self):
        self.assertTrue(create_parser().parse_args(["--list-all"]).list_all)

    def test_default_values(self):
        args = create_parser().parse_args([])
        self.assertEqual(args.limit, 50)
        self.assertEqual(args.days, 30)
        self.assertEqual(args.top, 10)
        self.assertEqual(args.max_output_lines, 1)
        self.assertFalse(args.desc)
        self.assertFalse(args.updated)


class TestShowConfig(unittest.TestCase):
    """Test _show_config function."""

    @patch("cursor_chronicle.cli.ensure_config_exists")
    def test_output(self, mock_ensure):
        mock_ensure.return_value = {"export_path": "/test/path", "verbosity": 2}
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
    def test_calls_export_dialogs(self, mock_summary, mock_export):
        mock_export.return_value = {"total_dialogs": 5, "exported": 5, "errors": 0,
                                    "skipped": 0, "export_path": "/tmp/test", "verbosity": 2}
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
    def test_with_custom_path(self, mock_summary, mock_export):
        mock_export.return_value = {"total_dialogs": 1, "exported": 1, "errors": 0,
                                    "skipped": 0, "export_path": "/custom/path", "verbosity": 3}
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

    def _capture_output(self, func, *args, **kwargs):
        captured = StringIO()
        sys.stdout = captured
        try:
            func(*args, **kwargs)
        finally:
            sys.stdout = sys.__stdout__
        return captured.getvalue()

    def test_no_projects(self):
        viewer = MagicMock()
        viewer.get_projects.return_value = []
        output = self._capture_output(show_dialog, viewer)
        self.assertIn("No projects found", output)

    def test_project_not_found(self):
        viewer = MagicMock()
        viewer.get_projects.return_value = [{"project_name": "other-project", "composers": []}]
        output = self._capture_output(show_dialog, viewer, project_name="nonexistent")
        self.assertIn("not found", output)

    def test_dialog_not_found(self):
        viewer = MagicMock()
        viewer.get_projects.return_value = [
            {"project_name": "test-project", "composers": [{"name": "other-dialog", "composerId": "123"}]}
        ]
        output = self._capture_output(show_dialog, viewer, project_name="test-project", dialog_name="nonexistent")
        self.assertIn("not found", output)

    def test_no_composers(self):
        viewer = MagicMock()
        viewer.get_projects.return_value = [{"project_name": "empty-project", "composers": []}]
        output = self._capture_output(show_dialog, viewer, project_name="empty-project")
        self.assertIn("No dialogs found", output)

    def test_no_composer_id(self):
        viewer = MagicMock()
        viewer.get_projects.return_value = [
            {"project_name": "test-project", "composers": [{"name": "test-dialog", "lastUpdatedAt": 1000}]}
        ]
        output = self._capture_output(show_dialog, viewer, project_name="test-project")
        self.assertIn("ID not found", output)

    @patch("cursor_chronicle.cli.get_dialog_messages")
    def test_no_messages(self, mock_get_messages):
        mock_get_messages.return_value = []
        viewer = MagicMock()
        viewer.get_projects.return_value = [
            {"project_name": "test-project", "composers": [{"name": "test-dialog", "composerId": "abc123", "lastUpdatedAt": 1000}]}
        ]
        output = self._capture_output(show_dialog, viewer, project_name="test-project")
        self.assertIn("No messages found", output)

    @patch("cursor_chronicle.cli.get_dialog_messages")
    def test_error_handling(self, mock_get_messages):
        mock_get_messages.side_effect = Exception("Database error")
        viewer = MagicMock()
        viewer.get_projects.return_value = [
            {"project_name": "test-project", "composers": [{"name": "test-dialog", "composerId": "abc123", "lastUpdatedAt": 1000}]}
        ]
        output = self._capture_output(show_dialog, viewer, project_name="test-project")
        self.assertIn("Error reading dialog", output)

    @patch("cursor_chronicle.cli.get_dialog_messages")
    @patch("cursor_chronicle.cli.format_dialog")
    def test_success(self, mock_format, mock_get_messages):
        mock_get_messages.return_value = [{"type": 1, "text": "Hello"}]
        mock_format.return_value = "Formatted dialog output"
        viewer = MagicMock()
        viewer.get_projects.return_value = [
            {"project_name": "test-project", "composers": [{"name": "test-dialog", "composerId": "abc123", "lastUpdatedAt": 1000}]}
        ]
        output = self._capture_output(show_dialog, viewer, project_name="test-project")
        self.assertIn("Formatted dialog output", output)

    @patch("cursor_chronicle.cli.get_dialog_messages")
    @patch("cursor_chronicle.cli.format_dialog")
    def test_finds_by_partial_name(self, mock_format, mock_get_messages):
        mock_get_messages.return_value = [{"type": 1, "text": "Hello"}]
        mock_format.return_value = "Output"
        viewer = MagicMock()
        viewer.get_projects.return_value = [
            {"project_name": "test-project", "composers": [{"name": "My Long Dialog Name", "composerId": "abc", "lastUpdatedAt": 1000}]}
        ]
        self._capture_output(show_dialog, viewer, project_name="test", dialog_name="long dialog")
        mock_get_messages.assert_called_once()


if __name__ == "__main__":
    unittest.main()
