"""
Tests for cross-platform Cursor path resolution.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from cursor_chronicle.utils import get_cursor_paths


class TestCursorPathResolution(unittest.TestCase):
    """Test get_cursor_paths platform and ENV resolution."""

    @patch("cursor_chronicle.utils.Path.home", return_value=Path("/home/test"))
    @patch("cursor_chronicle.utils.platform.system", return_value="Linux")
    def test_env_override_has_priority(self, _mock_platform, _mock_home):
        """CURSOR_USER_DIR should override platform defaults."""
        with patch.dict(
            os.environ, {"CURSOR_USER_DIR": "/custom/path/Cursor/User"}, clear=True
        ):
            cursor_config_path, workspace_storage_path, global_storage_path = (
                get_cursor_paths()
            )

        self.assertEqual(cursor_config_path, Path("/custom/path/Cursor/User"))
        self.assertEqual(
            workspace_storage_path, Path("/custom/path/Cursor/User/workspaceStorage")
        )
        self.assertEqual(
            global_storage_path,
            Path("/custom/path/Cursor/User/globalStorage/state.vscdb"),
        )

    @patch("cursor_chronicle.utils.Path.home", return_value=Path("/Users/test"))
    @patch("cursor_chronicle.utils.platform.system", return_value="Darwin")
    def test_macos_default_path(self, _mock_platform, _mock_home):
        """macOS should use ~/Library/Application Support/Cursor/User."""
        with patch.dict(os.environ, {}, clear=True):
            cursor_config_path, _, _ = get_cursor_paths()

        self.assertEqual(
            cursor_config_path,
            Path("/Users/test/Library/Application Support/Cursor/User"),
        )

    @patch("cursor_chronicle.utils.Path.home", return_value=Path("/home/test"))
    @patch("cursor_chronicle.utils.platform.system", return_value="Linux")
    def test_linux_default_path(self, _mock_platform, _mock_home):
        """Linux should use ~/.config/Cursor/User."""
        with patch.dict(os.environ, {}, clear=True):
            cursor_config_path, _, _ = get_cursor_paths()

        self.assertEqual(cursor_config_path, Path("/home/test/.config/Cursor/User"))

    @patch("cursor_chronicle.utils.Path.home", return_value=Path("/Users/fallback"))
    @patch("cursor_chronicle.utils.platform.system", return_value="Windows")
    def test_windows_uses_appdata_when_available(self, _mock_platform, _mock_home):
        """Windows should prefer %APPDATA% when present."""
        with patch.dict(
            os.environ, {"APPDATA": r"C:\Users\test\AppData\Roaming"}, clear=True
        ):
            cursor_config_path, _, _ = get_cursor_paths()

        self.assertEqual(
            cursor_config_path, Path(r"C:\Users\test\AppData\Roaming/Cursor/User")
        )

    @patch("cursor_chronicle.utils.Path.home", return_value=Path("/Users/test"))
    @patch("cursor_chronicle.utils.platform.system", return_value="Windows")
    def test_windows_fallback_without_appdata(self, _mock_platform, _mock_home):
        """Windows should fall back to ~/AppData/Roaming/Cursor/User."""
        with patch.dict(os.environ, {}, clear=True):
            cursor_config_path, workspace_storage_path, global_storage_path = (
                get_cursor_paths()
            )

        self.assertEqual(
            cursor_config_path, Path("/Users/test/AppData/Roaming/Cursor/User")
        )
        self.assertEqual(
            workspace_storage_path,
            Path("/Users/test/AppData/Roaming/Cursor/User/workspaceStorage"),
        )
        self.assertEqual(
            global_storage_path,
            Path("/Users/test/AppData/Roaming/Cursor/User/globalStorage/state.vscdb"),
        )
