"""
Tests for backup_formatters.py module and backup-related CLI/config integration.
"""

import json
import tempfile
import unittest
from pathlib import Path

from cursor_chronicle.backup import (
    format_backup_list,
    format_backup_summary,
    format_restore_summary,
)
from cursor_chronicle.backup_formatters import _format_size


class TestFormatSize(unittest.TestCase):
    """Test _format_size helper function."""

    def test_bytes(self):
        self.assertEqual(_format_size(500), "500 B")

    def test_zero(self):
        self.assertEqual(_format_size(0), "0 B")

    def test_kilobytes(self):
        result = _format_size(1536)
        self.assertIn("KB", result)
        self.assertIn("1.5", result)

    def test_megabytes(self):
        result = _format_size(5 * 1024 * 1024)
        self.assertIn("MB", result)
        self.assertIn("5.0", result)

    def test_gigabytes(self):
        result = _format_size(2 * 1024 * 1024 * 1024)
        self.assertIn("GB", result)
        self.assertIn("2.0", result)

    def test_boundary_kb(self):
        result = _format_size(1024)
        self.assertIn("KB", result)

    def test_boundary_mb(self):
        result = _format_size(1024 * 1024)
        self.assertIn("MB", result)


class TestFormatBackupSummary(unittest.TestCase):
    """Test format_backup_summary function."""

    def test_successful_backup(self):
        result = {
            "backup_path": "/tmp/backups/cursor_backup_2026-03-17_14-30-15.tar.xz",
            "total_files": 10,
            "total_size": 50 * 1024 * 1024,
            "compressed_size": 5 * 1024 * 1024,
            "compression_ratio": 90.0,
            "created_at": "2026-03-17T14:30:15",
        }

        output = format_backup_summary(result)
        self.assertIn("BACKUP SUMMARY", output)
        self.assertIn("cursor_backup_2026-03-17_14-30-15.tar.xz", output)
        self.assertIn("10", output)
        self.assertIn("90.0%", output)
        self.assertIn("✅", output)

    def test_error_result(self):
        result = {
            "backup_path": None,
            "total_files": 0,
            "total_size": 0,
            "compressed_size": 0,
            "compression_ratio": 0.0,
            "created_at": "2026-03-17T14:30:15",
            "error": "No Cursor files found to backup.",
        }

        output = format_backup_summary(result)
        self.assertIn("❌", output)
        self.assertIn("No Cursor files found", output)


class TestFormatBackupList(unittest.TestCase):
    """Test format_backup_list function."""

    def test_empty_list(self):
        output = format_backup_list([])
        self.assertIn("No backups found", output)
        self.assertIn("--backup", output)

    def test_with_backups(self):
        backups = [
            {
                "filename": "cursor_backup_2026-03-17_14-30-15.tar.xz",
                "path": "/tmp/backups/cursor_backup_2026-03-17_14-30-15.tar.xz",
                "size": 5 * 1024 * 1024,
                "created_at": "2026-03-17T14:30:15",
                "metadata": {
                    "total_files": 10,
                    "total_size_bytes": 50 * 1024 * 1024,
                },
            },
        ]

        output = format_backup_list(backups)
        self.assertIn("AVAILABLE BACKUPS", output)
        self.assertIn("cursor_backup_2026-03-17_14-30-15.tar.xz", output)
        self.assertIn("Total: 1 backup(s)", output)

    def test_multiple_backups(self):
        backups = [
            {
                "filename": f"cursor_backup_2026-03-{i:02d}_10-00-00.tar.xz",
                "path": f"/tmp/backups/cursor_backup_2026-03-{i:02d}_10-00-00.tar.xz",
                "size": 1024,
                "created_at": f"2026-03-{i:02d}T10:00:00",
                "metadata": None,
            }
            for i in range(1, 4)
        ]

        output = format_backup_list(backups)
        self.assertIn("Total: 3 backup(s)", output)


class TestFormatRestoreSummary(unittest.TestCase):
    """Test format_restore_summary function."""

    def test_successful_restore(self):
        result = {
            "restored_files": 10,
            "pre_restore_backup": "/tmp/backups/pre_restore.tar.xz",
            "errors": [],
            "success": True,
        }

        output = format_restore_summary(result)
        self.assertIn("RESTORE SUMMARY", output)
        self.assertIn("10", output)
        self.assertIn("✅", output)
        self.assertIn("pre_restore.tar.xz", output)
        self.assertIn("restart Cursor", output)

    def test_failed_restore(self):
        result = {
            "restored_files": 0,
            "pre_restore_backup": None,
            "errors": ["Backup file not found"],
            "success": False,
        }

        output = format_restore_summary(result)
        self.assertIn("❌", output)
        self.assertIn("Backup file not found", output)

    def test_restore_with_warnings(self):
        result = {
            "restored_files": 5,
            "pre_restore_backup": None,
            "errors": ["Warning: Could not create pre-restore backup"],
            "success": False,
        }

        output = format_restore_summary(result)
        self.assertIn("⚠️", output)


class TestCLIBackupArgs(unittest.TestCase):
    """Test CLI argument parsing for backup commands."""

    def setUp(self):
        from cursor_chronicle.cli import create_parser

        self.parser = create_parser()

    def test_backup_arg(self):
        args = self.parser.parse_args(["--backup"])
        self.assertTrue(args.backup)

    def test_list_backups_arg(self):
        args = self.parser.parse_args(["--list-backups"])
        self.assertTrue(args.list_backups)

    def test_restore_arg(self):
        args = self.parser.parse_args(["--restore", "latest"])
        self.assertEqual(args.restore, "latest")

    def test_restore_with_filename(self):
        args = self.parser.parse_args(["--restore", "cursor_backup_2026-03-17.tar.xz"])
        self.assertEqual(args.restore, "cursor_backup_2026-03-17.tar.xz")

    def test_backup_path_arg(self):
        args = self.parser.parse_args(["--backup", "--backup-path", "/custom/path"])
        self.assertTrue(args.backup)
        self.assertEqual(args.backup_path, "/custom/path")

    def test_no_pre_backup_arg(self):
        args = self.parser.parse_args(["--restore", "latest", "--no-pre-backup"])
        self.assertTrue(args.no_pre_backup)

    def test_default_no_pre_backup_false(self):
        args = self.parser.parse_args(["--restore", "latest"])
        self.assertFalse(args.no_pre_backup)

    def test_default_backup_path_none(self):
        args = self.parser.parse_args(["--backup"])
        self.assertIsNone(args.backup_path)


class TestConfigBackupPath(unittest.TestCase):
    """Test backup_path in config module."""

    def test_config_has_backup_path(self):
        from cursor_chronicle.config import DEFAULT_CONFIG

        self.assertIn("backup_path", DEFAULT_CONFIG)

    def test_get_backup_path_default(self):
        from cursor_chronicle.config import DEFAULT_BACKUP_PATH, get_backup_path

        result = get_backup_path({})
        self.assertEqual(result, DEFAULT_BACKUP_PATH)

    def test_get_backup_path_from_config(self):
        from cursor_chronicle.config import get_backup_path

        result = get_backup_path({"backup_path": "/my/backups"})
        self.assertEqual(result, Path("/my/backups"))

    def test_load_config_includes_backup_path(self):
        from cursor_chronicle.config import load_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_data = {"backup_path": "/custom/backups"}
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            config = load_config(config_path)
            self.assertEqual(config["backup_path"], "/custom/backups")


if __name__ == "__main__":
    unittest.main()
