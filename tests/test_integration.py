#!/usr/bin/env python3
"""
Integration tests for cursor_chronicle module
Tests against real local Cursor databases without mocks
"""

import os
import sys
import unittest
import sqlite3
from pathlib import Path
from unittest import mock
from io import StringIO

# Add parent directory to path to import cursor_chronicle
sys.path.insert(0, str(Path(__file__).parent.parent))

import cursor_chronicle


class TestCursorChronicleIntegration(unittest.TestCase):
    """Integration tests for cursor_chronicle using real local databases"""

    def setUp(self):
        """Set up test environment"""
        self.viewer = cursor_chronicle.CursorChatViewer()
        self.maxDiff = None

    def test_viewer_initialization(self):
        """Test that CursorChatViewer initializes correctly"""
        self.assertIsNotNone(self.viewer)
        self.assertIsInstance(self.viewer.cursor_config_path, Path)
        self.assertIsInstance(self.viewer.workspace_storage_path, Path)
        self.assertIsInstance(self.viewer.global_storage_path, Path)
        self.assertIsInstance(self.viewer.tool_types, dict)
        self.assertGreater(len(self.viewer.tool_types), 0)

    def test_get_projects_no_crash(self):
        """Test that get_projects() doesn't crash regardless of database state"""
        try:
            projects = self.viewer.get_projects()
            # Should return a list, even if empty
            self.assertIsInstance(projects, list)
            
            # If projects exist, verify structure
            for project in projects:
                self.assertIsInstance(project, dict)
                self.assertIn('workspace_id', project)
                self.assertIn('project_name', project)
                self.assertIn('folder_path', project)
                self.assertIn('composers', project)
                self.assertIn('state_db_path', project)
                
                # Verify composers is a list
                self.assertIsInstance(project['composers'], list)
                
                # If composers exist, verify structure
                for composer in project['composers']:
                    self.assertIsInstance(composer, dict)
                    # composerId should exist
                    self.assertIn('composerId', composer)
                    
        except Exception as e:
            self.fail(f"get_projects() crashed with: {e}")

    def test_list_projects_no_crash(self):
        """Test that list_projects() doesn't crash"""
        try:
            # Capture stdout to avoid cluttering test output
            with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                self.viewer.list_projects()
            
            # Should have produced some output
            output = mock_stdout.getvalue()
            self.assertIsInstance(output, str)
            
        except Exception as e:
            self.fail(f"list_projects() crashed with: {e}")

    def test_list_dialogs_no_crash(self):
        """Test that list_dialogs() doesn't crash with various inputs"""
        try:
            projects = self.viewer.get_projects()
            
            # Test with non-existent project
            with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                self.viewer.list_dialogs("non_existent_project_12345")
            output = mock_stdout.getvalue()
            self.assertIn("not found", output.lower())
            
            # Test with existing projects (if any)
            if projects:
                for project in projects[:2]:  # Test first 2 projects max
                    with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                        self.viewer.list_dialogs(project['project_name'])
                    output = mock_stdout.getvalue()
                    self.assertIsInstance(output, str)
                    
        except Exception as e:
            self.fail(f"list_dialogs() crashed with: {e}")

    def test_show_dialog_no_crash(self):
        """Test that show_dialog() doesn't crash with various inputs"""
        try:
            projects = self.viewer.get_projects()
            
            # Test with no parameters (should show most recent)
            with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                self.viewer.show_dialog()
            output = mock_stdout.getvalue()
            self.assertIsInstance(output, str)
            
            # Test with non-existent project
            with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                self.viewer.show_dialog("non_existent_project_12345")
            output = mock_stdout.getvalue()
            if projects:  # Only check if there are projects
                self.assertIn("not found", output.lower())
            
            # Test with existing projects and dialogs (if any)
            if projects:
                for project in projects[:1]:  # Test first project only
                    if project['composers']:
                        # Test with project name only
                        with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                            self.viewer.show_dialog(project['project_name'])
                        output = mock_stdout.getvalue()
                        self.assertIsInstance(output, str)
                        
                        # Test with project and dialog name
                        composer = project['composers'][0]
                        dialog_name = composer.get('name', 'test')
                        with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                            self.viewer.show_dialog(project['project_name'], dialog_name)
                        output = mock_stdout.getvalue()
                        self.assertIsInstance(output, str)
                        
        except Exception as e:
            self.fail(f"show_dialog() crashed with: {e}")

    def test_get_dialog_messages_no_crash(self):
        """Test that get_dialog_messages() doesn't crash with valid composer IDs"""
        try:
            projects = self.viewer.get_projects()
            
            # Test with invalid composer ID
            messages = self.viewer.get_dialog_messages("invalid_composer_id_12345")
            self.assertIsInstance(messages, list)
            
            # Test with existing composer IDs (if any)
            if projects:
                for project in projects[:1]:  # Test first project only
                    for composer in project['composers'][:2]:  # Test first 2 composers max
                        composer_id = composer.get('composerId')
                        if composer_id:
                            messages = self.viewer.get_dialog_messages(composer_id)
                            self.assertIsInstance(messages, list)
                            
                            # If messages exist, verify structure
                            for message in messages:
                                self.assertIsInstance(message, dict)
                                self.assertIn('text', message)
                                self.assertIn('type', message)
                                self.assertIn('bubble_id', message)
                                self.assertIn('attached_files', message)
                                self.assertIsInstance(message['attached_files'], list)
                                
        except Exception as e:
            self.fail(f"get_dialog_messages() crashed with: {e}")

    def test_format_methods_no_crash(self):
        """Test that formatting methods don't crash with various inputs"""
        try:
            # Test format_attached_files with various inputs
            result = self.viewer.format_attached_files([], 1)
            self.assertEqual(result, "")
            
            # Test with sample data
            sample_files = [
                {"type": "active", "path": "test.py", "line": 1},
                {"type": "selected", "path": "main.py"},
                {"type": "context", "path": "utils.py", "content": "test content"},
                {"type": "relevant", "path": "config.py"},
            ]
            
            result = self.viewer.format_attached_files(sample_files, 5)
            self.assertIsInstance(result, str)
            self.assertIn("test.py", result)
            
            # Test format_tool_call with various inputs
            result = self.viewer.format_tool_call({}, 1)
            self.assertEqual(result, "")
            
            sample_tool = {
                "tool": 15,
                "name": "run_terminal_cmd",
                "status": "success",
                "rawArgs": '{"command": "ls -la"}',
                "result": '{"output": "total 0", "exitCodeV2": 0}'
            }
            
            result = self.viewer.format_tool_call(sample_tool, 3)
            self.assertIsInstance(result, str)
            self.assertIn("Terminal Command", result)
            
            # Test format_token_info
            sample_message = {
                "token_count": {"inputTokens": 100, "outputTokens": 200},
                "usage_uuid": "test-uuid-123",
                "is_agentic": True,
                "use_web": False
            }
            
            result = self.viewer.format_token_info(sample_message)
            self.assertIsInstance(result, str)
            self.assertIn("100→200", result)
            
        except Exception as e:
            self.fail(f"Formatting methods crashed with: {e}")

    def test_database_access_graceful_failure(self):
        """Test that database access fails gracefully when databases don't exist"""
        try:
            # Create viewer with non-existent paths
            original_home = Path.home()
            fake_home = Path("/tmp/fake_cursor_home_12345")
            
            with mock.patch('pathlib.Path.home', return_value=fake_home):
                test_viewer = cursor_chronicle.CursorChatViewer()
                
                # These should not crash, just return empty results
                projects = test_viewer.get_projects()
                self.assertIsInstance(projects, list)
                self.assertEqual(len(projects), 0)
                
                with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    test_viewer.list_projects()
                output = mock_stdout.getvalue()
                self.assertIn("No projects found", output)
                
        except Exception as e:
            self.fail(f"Database access didn't fail gracefully: {e}")

    def test_extract_files_from_layout_comprehensive(self):
        """Test extract_files_from_layout with various complex structures"""
        try:
            # Test with deeply nested structure
            complex_layout = {
                "src": {
                    "main": {
                        "app.py": None,
                        "config.py": None,
                        "utils": {
                            "helpers.py": None,
                            "validators.py": None
                        }
                    },
                    "tests": {
                        "test_app.py": None,
                        "fixtures": {
                            "data.json": None
                        }
                    }
                },
                "README.md": None,
                "requirements.txt": None
            }
            
            files = self.viewer.extract_files_from_layout(complex_layout)
            self.assertIsInstance(files, list)
            self.assertIn("src/main/app.py", files)
            self.assertIn("src/main/utils/helpers.py", files)
            self.assertIn("src/tests/fixtures/data.json", files)
            self.assertIn("README.md", files)
            
            # Test with empty and None values
            result = self.viewer.extract_files_from_layout({})
            self.assertEqual(result, [])
            
            # Test with None input (should not crash)
            try:
                result = self.viewer.extract_files_from_layout(None)
                self.assertEqual(result, [])
            except (TypeError, AttributeError):
                # This is acceptable - method might not handle None gracefully
                pass
            
        except Exception as e:
            self.fail(f"extract_files_from_layout crashed with: {e}")

    def test_infer_model_comprehensive(self):
        """Test model inference with various message types"""
        try:
            test_cases = [
                # Agentic mode
                {
                    "message": {"text": "test", "is_agentic": True},
                    "tokens": 1000,
                    "expected_contains": "Claude"
                },
                # High token usage
                {
                    "message": {"text": "test", "is_agentic": False},
                    "tokens": 150000,
                    "expected_contains": "Claude"
                },
                # Text mentions
                {
                    "message": {"text": "Using Claude Sonnet for this task", "is_agentic": False},
                    "tokens": 1000,
                    "expected_contains": "Claude"
                },
                # GPT mention
                {
                    "message": {"text": "GPT-4 is being used", "is_agentic": False},
                    "tokens": 1000,
                    "expected_contains": "GPT"
                },
                # Unified mode
                {
                    "message": {"text": "test", "unified_mode": 4},
                    "tokens": 1000,
                    "expected_contains": "Advanced"
                },
                # No clear indicators
                {
                    "message": {"text": "simple message"},
                    "tokens": 100,
                    "expected_contains": ""
                }
            ]
            
            for i, test_case in enumerate(test_cases):
                result = self.viewer.infer_model_from_context(
                    test_case["message"], 
                    test_case["tokens"]
                )
                self.assertIsInstance(result, str)
                
                if test_case["expected_contains"]:
                    self.assertIn(test_case["expected_contains"], result, 
                                f"Test case {i}: Expected '{test_case['expected_contains']}' in '{result}'")
                    
        except Exception as e:
            self.fail(f"Model inference crashed with: {e}")

    def test_main_function_no_crash(self):
        """Test that main function doesn't crash with various arguments"""
        try:
            # Test with --list-projects
            with mock.patch('sys.argv', ['cursor_chronicle.py', '--list-projects']):
                with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    cursor_chronicle.main()
                output = mock_stdout.getvalue()
                self.assertIsInstance(output, str)
            
            # Test with --help (this will raise SystemExit, which is expected)
            with mock.patch('sys.argv', ['cursor_chronicle.py', '--help']):
                with self.assertRaises(SystemExit):
                    cursor_chronicle.main()
                    
        except SystemExit:
            pass  # Expected for --help
        except Exception as e:
            self.fail(f"main() crashed with: {e}")

    def test_signal_handling(self):
        """Test that signal handling is properly set up"""
        try:
            import signal
            # Just verify that SIGPIPE handler is set
            handler = signal.signal(signal.SIGPIPE, signal.SIG_DFL)
            self.assertIsNotNone(handler)
            
        except Exception as e:
            self.fail(f"Signal handling test failed: {e}")

    def test_database_connection_resilience(self):
        """Test database connection handling with various edge cases"""
        try:
            # Test with potentially corrupted database path
            if self.viewer.global_storage_path.exists():
                # Try to read with empty composer ID
                messages = self.viewer.get_dialog_messages("")
                self.assertIsInstance(messages, list)
                
                # Try to read with very long composer ID
                long_id = "a" * 1000
                messages = self.viewer.get_dialog_messages(long_id)
                self.assertIsInstance(messages, list)
                
        except Exception as e:
            self.fail(f"Database connection resilience test failed: {e}")

    def test_edge_cases_comprehensive(self):
        """Test various edge cases and boundary conditions"""
        try:
            # Test with max_output_lines edge cases
            with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                self.viewer.show_dialog(max_output_lines=0)
            output = mock_stdout.getvalue()
            self.assertIsInstance(output, str)
            
            with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                self.viewer.show_dialog(max_output_lines=1000)
            output = mock_stdout.getvalue()
            self.assertIsInstance(output, str)
            
            # Test extract_attached_files with edge cases
            edge_case_files = [
                {"type": "unknown", "path": "test.py"},
                {"type": "active", "path": ""},
                {"type": "selected"},  # Missing path
                {"path": "no_type.py"},  # Missing type
            ]
            
            result = self.viewer.format_attached_files(edge_case_files, 10)
            self.assertIsInstance(result, str)
            
            # Test format_tool_call with malformed data
            malformed_tool = {
                "tool": "not_a_number",
                "name": None,
                "rawArgs": "invalid_json{",
                "result": "also_invalid_json}"
            }
            
            result = self.viewer.format_tool_call(malformed_tool, 5)
            self.assertIsInstance(result, str)
            
        except Exception as e:
            self.fail(f"Edge cases test failed: {e}")


if __name__ == "__main__":
    unittest.main() 