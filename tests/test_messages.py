"""
Tests for messages.py module - message extraction and attached files.
"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cursor_chronicle


class TestExtractFilesFromLayout(unittest.TestCase):
    """Test extract_files_from_layout function."""

    def test_extract_files_from_layout_empty(self):
        """Test with empty layout."""
        result = cursor_chronicle.extract_files_from_layout({})
        self.assertEqual(result, [])

    def test_extract_files_from_layout_simple(self):
        """Test with simple layout."""
        layout = {
            "src": {"main.py": None, "utils.py": None, "tests": {"test_main.py": None}},
            "README.md": None,
        }
        files = cursor_chronicle.extract_files_from_layout(layout)
        expected_files = ["src/main.py", "src/utils.py", "src/tests/test_main.py", "README.md"]
        files.sort()
        expected_files.sort()
        self.assertEqual(files, expected_files)


class TestExtractAttachedFiles(unittest.TestCase):
    """Test extract_attached_files function."""

    def test_extract_attached_files_empty(self):
        """Test with empty bubble data."""
        result = cursor_chronicle.extract_attached_files({})
        self.assertEqual(result, [])

    def test_extract_attached_files_current_file(self):
        """Test extracting current file location."""
        bubble_data = {
            "currentFileLocationData": {
                "uri": "/path/to/file.py",
                "line": 42,
                "preview": "def test():",
            }
        }
        result = cursor_chronicle.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "active")
        self.assertEqual(result[0]["path"], "/path/to/file.py")
        self.assertEqual(result[0]["line"], 42)

    def test_extract_attached_files_current_file_path_field(self):
        """Test extracting current file with path field."""
        bubble_data = {"currentFileLocationData": {"path": "/path/to/file.py"}}
        result = cursor_chronicle.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["path"], "/path/to/file.py")

    def test_extract_attached_files_current_file_filepath_field(self):
        """Test extracting current file with filePath field."""
        bubble_data = {"currentFileLocationData": {"filePath": "/path/to/file.py"}}
        result = cursor_chronicle.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["path"], "/path/to/file.py")

    def test_extract_attached_files_current_file_file_field(self):
        """Test extracting current file with file field."""
        bubble_data = {"currentFileLocationData": {"file": "/path/to/file.py"}}
        result = cursor_chronicle.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["path"], "/path/to/file.py")

    def test_extract_attached_files_project_layouts_string(self):
        """Test extracting files from project layouts as JSON string."""
        layout = {"src": {"main.py": None}}
        bubble_data = {"projectLayouts": [json.dumps(layout)]}
        result = cursor_chronicle.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "project")
        self.assertEqual(result[0]["path"], "src/main.py")

    def test_extract_attached_files_project_layouts_invalid_json(self):
        """Test handling invalid JSON in project layouts."""
        bubble_data = {"projectLayouts": ["invalid json {"]}
        result = cursor_chronicle.extract_attached_files(bubble_data)
        self.assertEqual(result, [])

    def test_extract_attached_files_project_layouts_dict(self):
        """Test extracting files from project layouts as dict."""
        bubble_data = {"projectLayouts": [{"src": {"main.py": None}}]}
        result = cursor_chronicle.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "project")

    def test_extract_attached_files_codebase_context_chunks(self):
        """Test extracting codebase context chunks."""
        bubble_data = {
            "codebaseContextChunks": [
                {"relativeWorkspacePath": "src/utils.py", "contents": "def helper():", "lineRange": "10-20"}
            ]
        }
        result = cursor_chronicle.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "context")
        self.assertEqual(result[0]["path"], "src/utils.py")
        self.assertEqual(result[0]["content"], "def helper():")

    def test_extract_attached_files_relevant_files_dict(self):
        """Test extracting relevant files as dict."""
        bubble_data = {
            "relevantFiles": [{"path": "/path/to/file1.py"}, {"uri": "/path/to/file2.py"}]
        }
        result = cursor_chronicle.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["type"], "relevant")
        self.assertEqual(result[1]["type"], "relevant")

    def test_extract_attached_files_relevant_files_string(self):
        """Test extracting relevant files as string."""
        bubble_data = {"relevantFiles": ["/path/to/file.py"]}
        result = cursor_chronicle.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "relevant")
        self.assertEqual(result[0]["path"], "/path/to/file.py")

    def test_extract_attached_files_attached_code_chunks(self):
        """Test extracting attached code chunks."""
        bubble_data = {
            "attachedCodeChunks": [
                {"path": "/path/to/file.py", "content": "def test():", "selection": "1-10"}
            ]
        }
        result = cursor_chronicle.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "selected")
        self.assertEqual(result[0]["path"], "/path/to/file.py")

    def test_extract_attached_files_context_file_selections(self):
        """Test extracting file selections from context."""
        bubble_data = {
            "context": {"fileSelections": [{"path": "/path/to/file.py", "selection": "1-10"}]}
        }
        result = cursor_chronicle.extract_attached_files(bubble_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "selected_context")


class TestGetDialogMessages(unittest.TestCase):
    """Test get_dialog_messages function edge cases."""

    def test_get_dialog_messages_thinking_bubble(self):
        """Test thinking bubble detection."""
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')

        composer_data = {"fullConversationHeadersOnly": [{"bubbleId": "bubble1"}]}
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("composerData:test123", json.dumps(composer_data)))

        bubble_data = {
            "bubbleId": "bubble1",
            "type": 2,
            "text": "",
            "isThought": True,
            "thinkingDurationMs": 3000,
            "thinking": {"content": "Thinking about the problem..."},
        }
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("bubbleId:test123:bubble1", json.dumps(bubble_data)))

        conn.commit()
        conn.close()

        try:
            messages = cursor_chronicle.get_dialog_messages("test123", db_path=Path(db_path))
            self.assertEqual(len(messages), 1)
            self.assertTrue(messages[0]["is_thought"])
            self.assertEqual(messages[0]["thinking_duration"], 3000)
            self.assertIn("Thinking about", messages[0]["thinking_content"])
        finally:
            os.unlink(db_path)

    def test_get_dialog_messages_thinking_string(self):
        """Test thinking as string."""
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')

        composer_data = {"fullConversationHeadersOnly": [{"bubbleId": "bubble1"}]}
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("composerData:test123", json.dumps(composer_data)))

        bubble_data = {
            "bubbleId": "bubble1",
            "type": 2,
            "text": "",
            "thinking": "Direct thinking string" + " " * 100,
        }
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("bubbleId:test123:bubble1", json.dumps(bubble_data)))

        conn.commit()
        conn.close()

        try:
            messages = cursor_chronicle.get_dialog_messages("test123", db_path=Path(db_path))
            self.assertEqual(len(messages), 1)
            self.assertTrue(messages[0]["is_thought"])
            self.assertIn("Direct thinking string", messages[0]["thinking_content"])
        finally:
            os.unlink(db_path)

    def test_get_dialog_messages_no_full_conversation(self):
        """Test when no fullConversationHeadersOnly exists."""
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')

        composer_data = {"padding": "x" * 100}
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("composerData:test123", json.dumps(composer_data)))

        bubble_data = {"bubbleId": "bubble1", "type": 1, "text": "Hello " + "x" * 100}
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("bubbleId:test123:bubble1", json.dumps(bubble_data)))

        conn.commit()
        conn.close()

        try:
            messages = cursor_chronicle.get_dialog_messages("test123", db_path=Path(db_path))
            self.assertEqual(len(messages), 1)
        finally:
            os.unlink(db_path)

    def test_get_dialog_messages_json_decode_error(self):
        """Test handling of JSON decode error in bubble."""
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')

        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("bubbleId:test123:bubble1", "invalid json " + "x" * 100))

        conn.commit()
        conn.close()

        try:
            messages = cursor_chronicle.get_dialog_messages("test123", db_path=Path(db_path))
            self.assertEqual(len(messages), 0)
        finally:
            os.unlink(db_path)

    def test_thinking_bubble_base64_signature(self):
        """Test thinking bubble with base64-like signature is handled."""
        with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')

        composer_data = {"fullConversationHeadersOnly": [{"bubbleId": "bubble1"}], "padding": "x" * 100}
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("composerData:test123", json.dumps(composer_data)))

        bubble_data = {
            "bubbleId": "bubble1",
            "type": 2,
            "text": "",
            "isThought": True,
            "thinking": {"signature": "AVSoXOInvalidBase64Data" + "x" * 100},
        }
        cursor.execute("INSERT INTO cursorDiskKV VALUES (?, ?)",
                       ("bubbleId:test123:bubble1", json.dumps(bubble_data)))

        conn.commit()
        conn.close()

        try:
            messages = cursor_chronicle.get_dialog_messages("test123", db_path=Path(db_path))
            self.assertEqual(len(messages), 1)
            self.assertTrue(messages[0]["is_thought"])
        finally:
            os.unlink(db_path)


if __name__ == "__main__":
    unittest.main()
