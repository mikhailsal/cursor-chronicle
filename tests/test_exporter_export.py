"""
Tests for exporter.py module - Export dialogs functionality.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from cursor_chronicle.exporter import export_dialogs


class TestExportDialogs(unittest.TestCase):
    """Test export_dialogs function - integration with mock viewer."""

    def _make_viewer_mock(self, dialogs, messages_by_id=None):
        """Create a mock viewer with given dialogs."""
        viewer = MagicMock()
        viewer.get_all_dialogs.return_value = dialogs
        return viewer

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_export_creates_files(self, mock_get_messages, mock_load_config):
        """Test that export creates the correct file structure."""
        mock_load_config.return_value = {
            "export_path": "/tmp/test",
            "verbosity": 2,
        }

        mock_get_messages.return_value = [
            {
                "type": 1, "text": "Hello", "attached_files": [],
                "is_thought": False, "tool_data": None,
            },
            {
                "type": 2, "text": "Hi!", "attached_files": [],
                "is_thought": False, "tool_data": None,
                "token_count": {},
            },
        ]

        dialogs = [
            {
                "composer_id": "abc123",
                "name": "Test Dialog",
                "project_name": "myProject",
                "created_at": 1749736260000,  # 2025-06-12
                "last_updated": 1749736300000,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir)
            viewer = self._make_viewer_mock(dialogs)

            stats = export_dialogs(viewer, export_path=export_path, verbosity=2)

            self.assertEqual(stats["exported"], 1)
            self.assertEqual(stats["errors"], 0)

            # Check folder structure
            project_dir = export_path / "myProject"
            self.assertTrue(project_dir.exists())

            month_dir = project_dir / "2025-06"
            self.assertTrue(month_dir.exists())

            # Check file exists
            md_files = list(month_dir.glob("*.md"))
            self.assertEqual(len(md_files), 1)
            self.assertIn("Test_Dialog", md_files[0].name)

            # Check content
            content = md_files[0].read_text()
            self.assertIn("# Test Dialog", content)
            self.assertIn("Hello", content)
            self.assertIn("Hi!", content)

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_export_empty_dialog_skipped(self, mock_get_messages, mock_load_config):
        """Test that dialogs with no messages are skipped."""
        mock_load_config.return_value = {"export_path": "/tmp", "verbosity": 2}
        mock_get_messages.return_value = []

        dialogs = [
            {
                "composer_id": "abc123",
                "name": "Empty Dialog",
                "project_name": "myProject",
                "created_at": 1749736260000,
                "last_updated": 1749736260000,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            viewer = self._make_viewer_mock(dialogs)
            stats = export_dialogs(viewer, export_path=Path(tmpdir), verbosity=2)
            self.assertEqual(stats["skipped"], 1)
            self.assertEqual(stats["exported"], 0)

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_export_error_handling(self, mock_get_messages, mock_load_config):
        """Test that errors are counted but don't stop export."""
        mock_load_config.return_value = {"export_path": "/tmp", "verbosity": 2}
        mock_get_messages.side_effect = Exception("DB error")

        dialogs = [
            {
                "composer_id": "abc123",
                "name": "Bad Dialog",
                "project_name": "myProject",
                "created_at": 1749736260000,
                "last_updated": 1749736260000,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            viewer = self._make_viewer_mock(dialogs)
            stats = export_dialogs(viewer, export_path=Path(tmpdir), verbosity=2)
            self.assertEqual(stats["errors"], 1)
            self.assertEqual(stats["exported"], 0)

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_export_no_dialogs(self, mock_get_messages, mock_load_config):
        """Test export with no dialogs found."""
        mock_load_config.return_value = {"export_path": "/tmp", "verbosity": 2}

        with tempfile.TemporaryDirectory() as tmpdir:
            viewer = self._make_viewer_mock([])
            stats = export_dialogs(viewer, export_path=Path(tmpdir), verbosity=2)
            self.assertEqual(stats["total_dialogs"], 0)
            self.assertEqual(stats["exported"], 0)

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_export_multiple_projects(self, mock_get_messages, mock_load_config):
        """Test export with multiple projects creates separate folders."""
        mock_load_config.return_value = {"export_path": "/tmp", "verbosity": 2}
        mock_get_messages.return_value = [
            {
                "type": 1, "text": "Test", "attached_files": [],
                "is_thought": False, "tool_data": None,
            },
        ]

        dialogs = [
            {
                "composer_id": "id1",
                "name": "Dialog A",
                "project_name": "ProjectAlpha",
                "created_at": 1749736260000,
                "last_updated": 1749736260000,
            },
            {
                "composer_id": "id2",
                "name": "Dialog B",
                "project_name": "ProjectBeta",
                "created_at": 1749736260000,
                "last_updated": 1749736260000,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir)
            viewer = self._make_viewer_mock(dialogs)
            stats = export_dialogs(viewer, export_path=export_path, verbosity=2)

            self.assertEqual(stats["exported"], 2)
            self.assertTrue((export_path / "ProjectAlpha").exists())
            self.assertTrue((export_path / "ProjectBeta").exists())

    @patch("cursor_chronicle.exporter.load_config")
    @patch("cursor_chronicle.exporter.get_dialog_messages")
    def test_export_overwrites_existing(self, mock_get_messages, mock_load_config):
        """Test that export overwrites existing files."""
        mock_load_config.return_value = {"export_path": "/tmp", "verbosity": 2}
        mock_get_messages.return_value = [
            {
                "type": 1, "text": "Updated content", "attached_files": [],
                "is_thought": False, "tool_data": None,
            },
        ]

        dialogs = [
            {
                "composer_id": "abc123",
                "name": "Test Dialog",
                "project_name": "myProject",
                "created_at": 1749736260000,
                "last_updated": 1749736260000,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir)
            viewer = self._make_viewer_mock(dialogs)

            # First export
            export_dialogs(viewer, export_path=export_path, verbosity=2)

            # Second export (should overwrite)
            stats = export_dialogs(viewer, export_path=export_path, verbosity=2)
            self.assertEqual(stats["exported"], 1)

            # Check only one file exists
            md_files = list((export_path / "myProject" / "2025-06").glob("*.md"))
            self.assertEqual(len(md_files), 1)
            content = md_files[0].read_text()
            self.assertIn("Updated content", content)


if __name__ == "__main__":
    unittest.main()
