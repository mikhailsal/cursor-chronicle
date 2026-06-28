"""
Tests for backup.py module - backup creation, metadata, and file collection.
"""

import json
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cursor_chronicle.backup import (
    BACKUP_META_FILE,
    BACKUP_PREFIX,
    BACKUP_SUFFIX,
    DEFAULT_BACKUP_DIR,
    LZMA_PRESET,
    _build_backup_metadata,
    _collect_cursor_files,
    create_backup,
    get_backup_dir,
)


class TestGetBackupDir(unittest.TestCase):
    """Test get_backup_dir function."""

    def test_default_when_no_config(self):
        result = get_backup_dir(None)
        self.assertEqual(result, DEFAULT_BACKUP_DIR)

    def test_default_when_key_missing(self):
        result = get_backup_dir({"export_path": "/some/path"})
        self.assertEqual(result, DEFAULT_BACKUP_DIR)

    def test_from_config(self):
        result = get_backup_dir({"backup_path": "/custom/backups"})
        self.assertEqual(result, Path("/custom/backups"))

    def test_empty_config(self):
        result = get_backup_dir({})
        self.assertEqual(result, DEFAULT_BACKUP_DIR)


class TestBuildBackupMetadata(unittest.TestCase):
    """Test _build_backup_metadata function."""

    def test_basic_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            f1 = base / "file1.vscdb"
            f1.write_text("test data 1")
            f2 = base / "sub" / "file2.vscdb"
            f2.parent.mkdir()
            f2.write_text("test data 2")

            meta = _build_backup_metadata([f1, f2], base)

            self.assertEqual(meta["total_files"], 2)
            self.assertGreater(meta["total_size_bytes"], 0)
            self.assertIn("created_at", meta)
            self.assertEqual(str(base), meta["cursor_base_path"])
            self.assertEqual(len(meta["files"]), 2)

    def test_file_entries_have_required_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            f = base / "test.vscdb"
            f.write_text("data")

            meta = _build_backup_metadata([f], base)
            entry = meta["files"][0]

            self.assertIn("path", entry)
            self.assertIn("size", entry)
            self.assertIn("modified", entry)

    def test_empty_files_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta = _build_backup_metadata([], Path(tmpdir))
            self.assertEqual(meta["total_files"], 0)
            self.assertEqual(meta["total_size_bytes"], 0)
            self.assertEqual(meta["files"], [])

    def test_relative_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            f = base / "subdir" / "state.vscdb"
            f.parent.mkdir()
            f.write_text("data")

            meta = _build_backup_metadata([f], base)
            self.assertEqual(
                meta["files"][0]["path"], os.path.join("subdir", "state.vscdb")
            )


class TestCollectCursorFiles(unittest.TestCase):
    """Test _collect_cursor_files function."""

    @patch("cursor_chronicle.backup.get_cursor_paths")
    def test_no_files_exist(self, mock_paths):
        with tempfile.TemporaryDirectory() as tmpdir:
            cursor_path = Path(tmpdir) / "Cursor" / "User"
            ws_path = cursor_path / "workspaceStorage"
            global_path = cursor_path / "globalStorage" / "state.vscdb"
            mock_paths.return_value = (cursor_path, ws_path, global_path)

            base, files = _collect_cursor_files()
            self.assertEqual(files, [])

    @patch("cursor_chronicle.backup.get_cursor_paths")
    def test_collects_global_db(self, mock_paths):
        with tempfile.TemporaryDirectory() as tmpdir:
            cursor_path = Path(tmpdir) / "Cursor" / "User"
            ws_path = cursor_path / "workspaceStorage"
            global_dir = cursor_path / "globalStorage"
            global_dir.mkdir(parents=True)
            global_path = global_dir / "state.vscdb"
            global_path.write_text("global data")
            mock_paths.return_value = (cursor_path, ws_path, global_path)

            base, files = _collect_cursor_files()
            self.assertIn(global_path, files)

    @patch("cursor_chronicle.backup.get_cursor_paths")
    def test_collects_workspace_files(self, mock_paths):
        with tempfile.TemporaryDirectory() as tmpdir:
            cursor_path = Path(tmpdir) / "Cursor" / "User"
            ws_path = cursor_path / "workspaceStorage"
            global_path = cursor_path / "globalStorage" / "state.vscdb"
            mock_paths.return_value = (cursor_path, ws_path, global_path)

            ws1 = ws_path / "workspace1"
            ws1.mkdir(parents=True)
            (ws1 / "state.vscdb").write_text("ws1 data")
            (ws1 / "workspace.json").write_text('{"folder": "file:///test"}')

            base, files = _collect_cursor_files()
            self.assertEqual(len(files), 2)
            self.assertTrue(any(str(f).endswith("state.vscdb") for f in files))
            self.assertTrue(any(str(f).endswith("workspace.json") for f in files))

    @patch("cursor_chronicle.backup.get_cursor_paths")
    def test_skips_non_directories(self, mock_paths):
        with tempfile.TemporaryDirectory() as tmpdir:
            cursor_path = Path(tmpdir) / "Cursor" / "User"
            ws_path = cursor_path / "workspaceStorage"
            ws_path.mkdir(parents=True)
            global_path = cursor_path / "globalStorage" / "state.vscdb"
            mock_paths.return_value = (cursor_path, ws_path, global_path)

            stray = ws_path / "some_file.txt"
            stray.write_text("not a workspace")

            base, files = _collect_cursor_files()
            self.assertEqual(base, cursor_path.parent)
            self.assertIn(stray, files)


class TestCreateBackup(unittest.TestCase):
    """Test create_backup function."""

    @patch("cursor_chronicle.backup._collect_cursor_files")
    def test_no_files_to_backup(self, mock_collect):
        mock_collect.return_value = (Path("/tmp"), [])

        with tempfile.TemporaryDirectory() as tmpdir:
            result = create_backup(backup_dir=Path(tmpdir))

            self.assertIsNone(result["backup_path"])
            self.assertEqual(result["total_files"], 0)
            self.assertIn("error", result)

    @patch("cursor_chronicle.backup._collect_cursor_files")
    def test_creates_backup_file(self, mock_collect):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "cursor"
            base.mkdir()
            f1 = base / "state.vscdb"
            f1.write_text("database content " * 100)

            mock_collect.return_value = (base, [f1])
            backup_dir = Path(tmpdir) / "backups"

            result = create_backup(backup_dir=backup_dir)

            self.assertIsNotNone(result["backup_path"])
            self.assertTrue(Path(result["backup_path"]).exists())
            self.assertEqual(result["total_files"], 1)
            self.assertGreater(result["total_size"], 0)
            self.assertGreater(result["compressed_size"], 0)
            self.assertIn("compression_ratio", result)
            self.assertIn("created_at", result)

    @patch("cursor_chronicle.backup._collect_cursor_files")
    def test_backup_filename_format(self, mock_collect):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "cursor"
            base.mkdir()
            f1 = base / "state.vscdb"
            f1.write_text("data")

            mock_collect.return_value = (base, [f1])
            backup_dir = Path(tmpdir) / "backups"

            result = create_backup(backup_dir=backup_dir)
            filename = Path(result["backup_path"]).name

            self.assertTrue(filename.startswith(BACKUP_PREFIX))
            self.assertTrue(filename.endswith(BACKUP_SUFFIX))

    @patch("cursor_chronicle.backup._collect_cursor_files")
    def test_backup_is_valid_tar_xz(self, mock_collect):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "cursor"
            base.mkdir()
            f1 = base / "state.vscdb"
            f1.write_text("database content")

            mock_collect.return_value = (base, [f1])
            backup_dir = Path(tmpdir) / "backups"

            result = create_backup(backup_dir=backup_dir)

            with tarfile.open(result["backup_path"], "r:xz") as tar:
                names = tar.getnames()
                self.assertIn(BACKUP_META_FILE, names)
                self.assertIn("state.vscdb", names)

    @patch("cursor_chronicle.backup._collect_cursor_files")
    def test_backup_contains_metadata(self, mock_collect):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "cursor"
            base.mkdir()
            f1 = base / "state.vscdb"
            f1.write_text("data")

            mock_collect.return_value = (base, [f1])
            backup_dir = Path(tmpdir) / "backups"

            result = create_backup(backup_dir=backup_dir)

            with tarfile.open(result["backup_path"], "r:xz") as tar:
                meta_file = tar.extractfile(BACKUP_META_FILE)
                meta = json.loads(meta_file.read().decode("utf-8"))
                self.assertIn("created_at", meta)
                self.assertIn("total_files", meta)
                self.assertIn("files", meta)

    @patch("cursor_chronicle.backup._collect_cursor_files")
    def test_progress_callback(self, mock_collect):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "cursor"
            base.mkdir()
            f1 = base / "file1.vscdb"
            f1.write_text("data1")
            f2 = base / "file2.vscdb"
            f2.write_text("data2")

            mock_collect.return_value = (base, [f1, f2])
            backup_dir = Path(tmpdir) / "backups"

            progress_calls = []
            result = create_backup(
                backup_dir=backup_dir,
                progress_callback=lambda info: progress_calls.append(info),
            )

            self.assertGreaterEqual(len(progress_calls), 2)
            self.assertEqual(progress_calls[0]["current"], 1)
            self.assertEqual(progress_calls[-1]["current"], 2)
            self.assertEqual(progress_calls[-1]["percent"], 100)
            self.assertIn("bytes_processed", progress_calls[-1])
            self.assertIn("bytes_total", progress_calls[-1])

    @patch("cursor_chronicle.backup._collect_cursor_files")
    def test_creates_backup_dir(self, mock_collect):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "cursor"
            base.mkdir()
            f1 = base / "state.vscdb"
            f1.write_text("data")

            mock_collect.return_value = (base, [f1])
            backup_dir = Path(tmpdir) / "deep" / "nested" / "backups"

            result = create_backup(backup_dir=backup_dir)
            self.assertTrue(backup_dir.exists())

    @patch("cursor_chronicle.backup._collect_cursor_files")
    def test_interrupted_backup_removes_partial_file(self, mock_collect):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "cursor"
            base.mkdir()
            f1 = base / "state.vscdb"
            f1.write_text("data")

            mock_collect.return_value = (base, [f1])
            backup_dir = Path(tmpdir) / "backups"

            def _failing_open(path, mode="r", **kwargs):
                Path(path).write_bytes(b"partial")
                raise RuntimeError("simulated interruption")

            with patch(
                "cursor_chronicle.backup.tarfile.open", side_effect=_failing_open
            ):
                with self.assertRaises(RuntimeError):
                    create_backup(backup_dir=backup_dir)

            leftovers = (
                [p.name for p in backup_dir.iterdir()] if backup_dir.exists() else []
            )
            self.assertFalse(any(name.endswith(".partial") for name in leftovers))
            self.assertFalse(any(name.endswith(BACKUP_SUFFIX) for name in leftovers))

    @patch("cursor_chronicle.backup._collect_cursor_files")
    def test_compression_is_effective(self, mock_collect):
        """Test that LZMA compression actually reduces size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "cursor"
            base.mkdir()
            f1 = base / "state.vscdb"
            f1.write_text("SELECT * FROM table WHERE id = 1;\n" * 1000)

            mock_collect.return_value = (base, [f1])
            backup_dir = Path(tmpdir) / "backups"

            result = create_backup(backup_dir=backup_dir)

            self.assertGreater(result["compression_ratio"], 50.0)
            self.assertLess(result["compressed_size"], result["total_size"])


class TestConstants(unittest.TestCase):
    """Test module constants."""

    def test_backup_prefix(self):
        self.assertEqual(BACKUP_PREFIX, "cursor_backup_")

    def test_backup_suffix(self):
        self.assertEqual(BACKUP_SUFFIX, ".tar.xz")

    def test_lzma_preset_max(self):
        self.assertEqual(LZMA_PRESET, 3)

    def test_meta_filename(self):
        self.assertEqual(BACKUP_META_FILE, "backup_meta.json")


if __name__ == "__main__":
    unittest.main()
