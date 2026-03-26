"""
Tests for OS-specific and overridable Cursor User directory resolution.
"""

import os
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from cursor_chronicle.utils import (  # noqa: E402
    CURSOR_USER_DIR_ENV,
    get_cursor_paths,
)


@contextmanager
def _without_cursor_user_env():
    saved = os.environ.pop(CURSOR_USER_DIR_ENV, None)
    try:
        yield
    finally:
        if saved is not None:
            os.environ[CURSOR_USER_DIR_ENV] = saved


class TestCursorUserDirEnv(unittest.TestCase):
    """CURSOR_CHRONICLE_CURSOR_USER_DIR overrides defaults."""

    def test_override_used(self):
        with patch.dict(os.environ, {CURSOR_USER_DIR_ENV: "/custom/Cursor/User"}):
            base, ws, gs = get_cursor_paths()
        self.assertEqual(base, Path("/custom/Cursor/User"))
        self.assertEqual(ws, Path("/custom/Cursor/User/workspaceStorage"))
        self.assertEqual(gs, Path("/custom/Cursor/User/globalStorage/state.vscdb"))

    def test_override_expanduser(self):
        with patch.dict(os.environ, {CURSOR_USER_DIR_ENV: "~/my-cursor/User"}):
            base, _, _ = get_cursor_paths()
        self.assertEqual(base, Path.home() / "my-cursor/User")

    def test_empty_override_ignored(self):
        with patch.dict(os.environ, {CURSOR_USER_DIR_ENV: "   "}):
            with patch("cursor_chronicle.utils.sys.platform", "linux"):
                with patch(
                    "cursor_chronicle.utils.Path.home",
                    return_value=Path("/home/x"),
                ):
                    base, _, _ = get_cursor_paths()
        self.assertEqual(base, Path("/home/x/.config/Cursor/User"))

    def test_linux_default_when_unset(self):
        with _without_cursor_user_env():
            with patch("cursor_chronicle.utils.sys.platform", "linux"):
                with patch(
                    "cursor_chronicle.utils.Path.home",
                    return_value=Path("/home/x"),
                ):
                    base, _, _ = get_cursor_paths()
        self.assertEqual(base, Path("/home/x/.config/Cursor/User"))

    def test_darwin_default_when_unset(self):
        with _without_cursor_user_env():
            with patch("cursor_chronicle.utils.sys.platform", "darwin"):
                with patch(
                    "cursor_chronicle.utils.Path.home",
                    return_value=Path("/Users/x"),
                ):
                    base, _, _ = get_cursor_paths()
        expected = (
            Path("/Users/x")
            / "Library"
            / "Application Support"
            / "Cursor"
            / "User"
        )
        self.assertEqual(base, expected)


if __name__ == "__main__":
    unittest.main()
