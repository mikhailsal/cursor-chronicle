"""
Tests for config.py module - configuration management.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cursor_chronicle.config import (
    DEFAULT_CONFIG,
    DEFAULT_EXPORT_PATH,
    VERBOSITY_COMPACT,
    VERBOSITY_FULL,
    VERBOSITY_STANDARD,
    ensure_config_exists,
    get_export_path,
    get_verbosity,
    load_config,
    save_config,
)


class TestLoadConfig(unittest.TestCase):
    """Test load_config function."""

    def test_load_config_no_file(self):
        """Test loading config when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent" / "config.json"
            config = load_config(config_path)
            self.assertEqual(config["export_path"], str(DEFAULT_EXPORT_PATH))
            self.assertEqual(config["verbosity"], VERBOSITY_STANDARD)

    def test_load_config_valid_file(self):
        """Test loading config from a valid file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_data = {"export_path": "/custom/path", "verbosity": 3}
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            config = load_config(config_path)
            self.assertEqual(config["export_path"], "/custom/path")
            self.assertEqual(config["verbosity"], 3)

    def test_load_config_partial_file(self):
        """Test loading config with only some keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_data = {"verbosity": 1}
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            config = load_config(config_path)
            self.assertEqual(config["export_path"], str(DEFAULT_EXPORT_PATH))
            self.assertEqual(config["verbosity"], 1)

    def test_load_config_invalid_json(self):
        """Test loading config with invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            with open(config_path, "w") as f:
                f.write("not valid json {{{")

            config = load_config(config_path)
            self.assertEqual(config, DEFAULT_CONFIG)

    def test_load_config_not_a_dict(self):
        """Test loading config where JSON is not a dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            with open(config_path, "w") as f:
                json.dump([1, 2, 3], f)

            config = load_config(config_path)
            self.assertEqual(config, DEFAULT_CONFIG)

    def test_load_config_extra_keys_ignored(self):
        """Test that extra keys in config file are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_data = {
                "export_path": "/custom",
                "verbosity": 1,
                "unknown_key": "value",
            }
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            config = load_config(config_path)
            self.assertEqual(config["export_path"], "/custom")
            self.assertNotIn("unknown_key", config)


class TestSaveConfig(unittest.TestCase):
    """Test save_config function."""

    def test_save_config_creates_file(self):
        """Test that save_config creates the config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config = {"export_path": "/test/path", "verbosity": 2}
            save_config(config, config_path)

            self.assertTrue(config_path.exists())
            with open(config_path) as f:
                saved = json.load(f)
            self.assertEqual(saved["export_path"], "/test/path")

    def test_save_config_creates_parent_dirs(self):
        """Test that save_config creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sub" / "dir" / "config.json"
            save_config(DEFAULT_CONFIG, config_path)
            self.assertTrue(config_path.exists())

    def test_save_config_overwrites(self):
        """Test that save_config overwrites existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            save_config({"export_path": "/first", "verbosity": 1}, config_path)
            save_config({"export_path": "/second", "verbosity": 3}, config_path)

            with open(config_path) as f:
                saved = json.load(f)
            self.assertEqual(saved["export_path"], "/second")
            self.assertEqual(saved["verbosity"], 3)


class TestEnsureConfigExists(unittest.TestCase):
    """Test ensure_config_exists function."""

    def test_creates_config_if_missing(self):
        """Test that config file is created when missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config = ensure_config_exists(config_path)

            self.assertTrue(config_path.exists())
            self.assertEqual(config["export_path"], str(DEFAULT_EXPORT_PATH))

    def test_loads_existing_config(self):
        """Test that existing config is loaded without overwriting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            with open(config_path, "w") as f:
                json.dump({"export_path": "/custom", "verbosity": 3}, f)

            config = ensure_config_exists(config_path)
            self.assertEqual(config["export_path"], "/custom")
            self.assertEqual(config["verbosity"], 3)


class TestGetExportPath(unittest.TestCase):
    """Test get_export_path function."""

    def test_from_config_dict(self):
        """Test getting export path from config dict."""
        config = {"export_path": "/my/export/path"}
        result = get_export_path(config)
        self.assertEqual(result, Path("/my/export/path"))

    def test_default_when_missing(self):
        """Test default export path when key is missing."""
        result = get_export_path({})
        self.assertEqual(result, DEFAULT_EXPORT_PATH)


class TestGetVerbosity(unittest.TestCase):
    """Test get_verbosity function."""

    def test_valid_verbosity(self):
        """Test getting valid verbosity levels."""
        self.assertEqual(get_verbosity({"verbosity": 1}), VERBOSITY_COMPACT)
        self.assertEqual(get_verbosity({"verbosity": 2}), VERBOSITY_STANDARD)
        self.assertEqual(get_verbosity({"verbosity": 3}), VERBOSITY_FULL)

    def test_invalid_verbosity_too_low(self):
        """Test that invalid low verbosity returns default."""
        self.assertEqual(get_verbosity({"verbosity": 0}), VERBOSITY_STANDARD)

    def test_invalid_verbosity_too_high(self):
        """Test that invalid high verbosity returns default."""
        self.assertEqual(get_verbosity({"verbosity": 5}), VERBOSITY_STANDARD)

    def test_invalid_verbosity_not_int(self):
        """Test that non-int verbosity returns default."""
        self.assertEqual(get_verbosity({"verbosity": "high"}), VERBOSITY_STANDARD)

    def test_missing_verbosity(self):
        """Test default when verbosity key is missing."""
        self.assertEqual(get_verbosity({}), VERBOSITY_STANDARD)


class TestVerbosityConstants(unittest.TestCase):
    """Test verbosity level constants."""

    def test_verbosity_values(self):
        """Test that verbosity constants have expected values."""
        self.assertEqual(VERBOSITY_COMPACT, 1)
        self.assertEqual(VERBOSITY_STANDARD, 2)
        self.assertEqual(VERBOSITY_FULL, 3)

    def test_verbosity_ordering(self):
        """Test that verbosity levels are ordered."""
        self.assertLess(VERBOSITY_COMPACT, VERBOSITY_STANDARD)
        self.assertLess(VERBOSITY_STANDARD, VERBOSITY_FULL)


if __name__ == "__main__":
    unittest.main()
