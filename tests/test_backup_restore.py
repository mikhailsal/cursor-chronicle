"""
Tests for backup.py module - list, validate, and restore functionality.
"""

import io
import tarfile
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from cursor_chronicle.backup import (
    BACKUP_META_FILE,
    BACKUP_PREFIX,
    BACKUP_SUFFIX,
    _validate_backup,
    create_backup,
    list_backups,
    restore_backup,
)


class TestListBackups(unittest.TestCase):
    """Test list_backups function."""

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = list_backups(backup_dir=Path(tmpdir))
            self.assertEqual(result, [])

    def test_nonexistent_directory(self):
        result = list_backups(backup_dir=Path("/nonexistent/path"))
        self.assertEqual(result, [])

    @patch("cursor_chronicle.backup._collect_cursor_files")
    def test_lists_created_backups(self, mock_collect):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "cursor"
            base.mkdir()
            f1 = base / "state.vscdb"
            f1.write_text("data")

            mock_collect.return_value = (base, [f1])
            backup_dir = Path(tmpdir) / "backups"

            create_backup(backup_dir=backup_dir)

            backups = list_backups(backup_dir=backup_dir)
            self.assertEqual(len(backups), 1)
            self.assertIn("filename", backups[0])
            self.assertIn("path", backups[0])
            self.assertIn("size", backups[0])

    def test_ignores_non_backup_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir)
            (backup_dir / "random_file.txt").write_text("not a backup")
            (backup_dir / "other.tar.gz").write_text("also not")

            result = list_backups(backup_dir=backup_dir)
            self.assertEqual(result, [])

    @patch("cursor_chronicle.backup._collect_cursor_files")
    def test_sorted_newest_first(self, mock_collect):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "cursor"
            base.mkdir()
            f1 = base / "state.vscdb"
            f1.write_text("data")

            mock_collect.return_value = (base, [f1])
            backup_dir = Path(tmpdir) / "backups"

            create_backup(backup_dir=backup_dir)
            time.sleep(1.1)
            create_backup(backup_dir=backup_dir)

            backups = list_backups(backup_dir=backup_dir)
            self.assertEqual(len(backups), 2)
            self.assertGreaterEqual(
                backups[0].get("created_at", ""),
                backups[1].get("created_at", ""),
            )

    @patch("cursor_chronicle.backup._collect_cursor_files")
    def test_backup_has_metadata(self, mock_collect):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "cursor"
            base.mkdir()
            f1 = base / "state.vscdb"
            f1.write_text("data")

            mock_collect.return_value = (base, [f1])
            backup_dir = Path(tmpdir) / "backups"

            create_backup(backup_dir=backup_dir)
            backups = list_backups(backup_dir=backup_dir)

            self.assertIsNotNone(backups[0]["metadata"])
            self.assertIn("total_files", backups[0]["metadata"])

    def test_handles_corrupted_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir)
            fake = backup_dir / f"{BACKUP_PREFIX}2026-03-17_10-00-00{BACKUP_SUFFIX}"
            fake.write_text("this is not a valid tar.xz file")

            backups = list_backups(backup_dir=backup_dir)
            self.assertEqual(len(backups), 1)
            self.assertIsNone(backups[0]["metadata"])

    def test_list_backups_cleans_partial_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir)
            partial = backup_dir / f".{BACKUP_PREFIX}2026-03-17_10-00-00{BACKUP_SUFFIX}.partial"
            partial.write_text("partial")

            backups = list_backups(backup_dir=backup_dir)

            self.assertEqual(backups, [])
            self.assertFalse(partial.exists())


class TestValidateBackup(unittest.TestCase):
    """Test _validate_backup function."""

    def test_nonexistent_file(self):
        is_valid, msg, meta = _validate_backup(Path("/nonexistent/backup.tar.xz"))
        self.assertFalse(is_valid)
        self.assertIn("not found", msg)

    def test_not_a_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            is_valid, msg, meta = _validate_backup(Path(tmpdir))
            self.assertFalse(is_valid)
            self.assertIn("Not a file", msg)

    def test_corrupted_archive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake = Path(tmpdir) / "bad.tar.xz"
            fake.write_text("corrupted data")
            is_valid, msg, meta = _validate_backup(fake)
            self.assertFalse(is_valid)
            self.assertIn("Invalid", msg)

    @patch("cursor_chronicle.backup._collect_cursor_files")
    def test_valid_backup(self, mock_collect):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "cursor"
            base.mkdir()
            f1 = base / "state.vscdb"
            f1.write_text("data")

            mock_collect.return_value = (base, [f1])
            backup_dir = Path(tmpdir) / "backups"

            result = create_backup(backup_dir=backup_dir)
            is_valid, msg, meta = _validate_backup(Path(result["backup_path"]))

            self.assertTrue(is_valid)
            self.assertIn("valid", msg.lower())
            self.assertIsNotNone(meta)

    def test_archive_without_vscdb(self):
        """Test that backup without .vscdb files is invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = Path(tmpdir) / f"{BACKUP_PREFIX}test{BACKUP_SUFFIX}"

            with tarfile.open(str(archive_path), "w:xz") as tar:
                data = b"just text"
                info = tarfile.TarInfo(name="readme.txt")
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))

            is_valid, msg, meta = _validate_backup(archive_path)
            self.assertFalse(is_valid)
            self.assertIn("no database files", msg.lower())


class TestRestoreBackup(unittest.TestCase):
    """Test restore_backup function."""

    @patch("cursor_chronicle.backup._collect_cursor_files")
    @patch("cursor_chronicle.backup.get_cursor_paths")
    def test_restore_basic(self, mock_paths, mock_collect):
        with tempfile.TemporaryDirectory() as tmpdir:
            cursor_base = Path(tmpdir) / "cursor_base"
            cursor_base.mkdir()
            gs_dir = cursor_base / "globalStorage"
            gs_dir.mkdir()
            original_db = gs_dir / "state.vscdb"
            original_db.write_text("original data for backup")

            mock_paths.return_value = (
                cursor_base,
                cursor_base / "workspaceStorage",
                original_db,
            )
            mock_collect.return_value = (cursor_base, [original_db])

            backup_dir = Path(tmpdir) / "backups"

            backup_result = create_backup(backup_dir=backup_dir)
            self.assertIsNotNone(backup_result["backup_path"])

            original_db.write_text("modified data after backup")
            self.assertEqual(original_db.read_text(), "modified data after backup")

            restore_result = restore_backup(
                backup_path=Path(backup_result["backup_path"]),
                create_pre_restore_backup=False,
                backup_dir=backup_dir,
            )

            self.assertTrue(restore_result["success"])
            self.assertGreater(restore_result["restored_files"], 0)
            self.assertEqual(original_db.read_text(), "original data for backup")

    def test_restore_invalid_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake = Path(tmpdir) / "bad.tar.xz"
            fake.write_text("not valid")

            result = restore_backup(
                backup_path=fake,
                create_pre_restore_backup=False,
            )

            self.assertFalse(result["success"])
            self.assertGreater(len(result["errors"]), 0)

    def test_restore_nonexistent_backup(self):
        result = restore_backup(
            backup_path=Path("/nonexistent/backup.tar.xz"),
            create_pre_restore_backup=False,
        )

        self.assertFalse(result["success"])
        self.assertGreater(len(result["errors"]), 0)

    @patch("cursor_chronicle.backup._collect_cursor_files")
    @patch("cursor_chronicle.backup.get_cursor_paths")
    def test_restore_with_pre_backup(self, mock_paths, mock_collect):
        with tempfile.TemporaryDirectory() as tmpdir:
            cursor_base = Path(tmpdir) / "cursor_base"
            cursor_base.mkdir()
            gs_dir = cursor_base / "globalStorage"
            gs_dir.mkdir()
            original_db = gs_dir / "state.vscdb"
            original_db.write_text("data v1")

            mock_paths.return_value = (
                cursor_base,
                cursor_base / "workspaceStorage",
                original_db,
            )
            mock_collect.return_value = (cursor_base, [original_db])

            backup_dir = Path(tmpdir) / "backups"

            backup_result = create_backup(backup_dir=backup_dir)

            time.sleep(1.1)

            original_db.write_text("data v2")
            mock_collect.return_value = (cursor_base, [original_db])

            restore_result = restore_backup(
                backup_path=Path(backup_result["backup_path"]),
                create_pre_restore_backup=True,
                backup_dir=backup_dir,
            )

            self.assertTrue(restore_result["success"])
            self.assertIsNotNone(restore_result["pre_restore_backup"])

            backups = list_backups(backup_dir=backup_dir)
            self.assertEqual(len(backups), 2)

    @patch("cursor_chronicle.backup._collect_cursor_files")
    @patch("cursor_chronicle.backup.get_cursor_paths")
    def test_restore_progress_callback(self, mock_paths, mock_collect):
        with tempfile.TemporaryDirectory() as tmpdir:
            cursor_base = Path(tmpdir) / "cursor_base"
            cursor_base.mkdir()
            gs_dir = cursor_base / "globalStorage"
            gs_dir.mkdir()
            db = gs_dir / "state.vscdb"
            db.write_text("data")

            mock_paths.return_value = (
                cursor_base,
                cursor_base / "workspaceStorage",
                db,
            )
            mock_collect.return_value = (cursor_base, [db])

            backup_dir = Path(tmpdir) / "backups"
            backup_result = create_backup(backup_dir=backup_dir)

            progress_calls = []
            restore_backup(
                backup_path=Path(backup_result["backup_path"]),
                create_pre_restore_backup=False,
                progress_callback=lambda info: progress_calls.append(info),
            )

            self.assertGreater(len(progress_calls), 0)
            self.assertEqual(progress_calls[-1]["percent"], 100)


if __name__ == "__main__":
    unittest.main()
