"""
Tests for statistics.py module - statistics collection and formatting.
"""

import sys
import unittest
from collections import Counter
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cursor_chronicle


class TestStatisticsFeature(unittest.TestCase):
    """Test the statistics functionality."""

    def test_get_dialog_statistics_returns_dict(self):
        """Test that get_dialog_statistics returns a dictionary."""
        viewer = cursor_chronicle.CursorChatViewer()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        result = cursor_chronicle.get_dialog_statistics(viewer, start_date=start_date, end_date=end_date)
        self.assertIsInstance(result, dict)

    def test_get_dialog_statistics_has_required_keys(self):
        """Test that statistics dict has required keys."""
        viewer = cursor_chronicle.CursorChatViewer()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        result = cursor_chronicle.get_dialog_statistics(viewer, start_date=start_date, end_date=end_date)

        required_keys = ["period_start", "period_end", "total_dialogs", "projects"]
        for key in required_keys:
            self.assertIn(key, result)

    def test_get_dialog_statistics_with_date_filter(self):
        """Test statistics with date filtering."""
        viewer = cursor_chronicle.CursorChatViewer()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        result = cursor_chronicle.get_dialog_statistics(viewer, start_date=start_date, end_date=end_date)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["period_start"], start_date)
        self.assertEqual(result["period_end"], end_date)

    def test_get_dialog_statistics_with_project_filter(self):
        """Test statistics with project filtering."""
        viewer = cursor_chronicle.CursorChatViewer()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        projects = viewer.get_projects()
        if projects:
            project_name = projects[0]["project_name"]
            result = cursor_chronicle.get_dialog_statistics(viewer, start_date=start_date, end_date=end_date, project_filter=project_name)

            self.assertIsInstance(result, dict)
            for proj_name in result.get("projects", {}).keys():
                self.assertIn(project_name.lower(), proj_name.lower())

    def test_statistics_counts_are_non_negative(self):
        """Test that all counts in statistics are non-negative."""
        viewer = cursor_chronicle.CursorChatViewer()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        result = cursor_chronicle.get_dialog_statistics(viewer, start_date=start_date, end_date=end_date)

        if result["total_dialogs"] > 0:
            self.assertGreaterEqual(result.get("total_messages", 0), 0)
            self.assertGreaterEqual(result.get("user_messages", 0), 0)
            self.assertGreaterEqual(result.get("ai_messages", 0), 0)
            self.assertGreaterEqual(result.get("tool_calls", 0), 0)
            self.assertGreaterEqual(result.get("total_tokens_in", 0), 0)
            self.assertGreaterEqual(result.get("total_tokens_out", 0), 0)

    def test_daily_activity_in_stats(self):
        """Test that daily_activity is properly populated."""
        viewer = cursor_chronicle.CursorChatViewer()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        result = cursor_chronicle.get_dialog_statistics(viewer, start_date=start_date, end_date=end_date)

        self.assertIn("daily_activity", result)
        self.assertIsInstance(result["daily_activity"], dict)


class TestFormatStatistics(unittest.TestCase):
    """Test format_statistics function."""

    def test_format_statistics_empty_stats(self):
        """Test format_statistics with empty data."""
        empty_stats = {"period_start": None, "period_end": None, "total_dialogs": 0, "projects": {}}
        result = cursor_chronicle.format_statistics(empty_stats)
        self.assertIn("No dialogs found", result)

    def test_format_statistics_with_data(self):
        """Test format_statistics with sample data."""
        sample_stats = {
            "period_start": datetime(2024, 1, 1),
            "period_end": datetime(2024, 1, 31),
            "total_dialogs": 5,
            "total_messages": 100,
            "user_messages": 30,
            "ai_messages": 70,
            "tool_calls": 50,
            "thinking_bubbles": 10,
            "total_tokens_in": 10000,
            "total_tokens_out": 5000,
            "total_thinking_time_ms": 30000,
            "projects": {
                "test-project": {
                    "dialogs": 5, "messages": 100, "user_messages": 30, "ai_messages": 70,
                    "tool_calls": 50, "tokens_in": 10000, "tokens_out": 5000, "dialog_names": ["Dialog 1", "Dialog 2"],
                }
            },
            "tool_usage": Counter({"read_file": 20, "edit_file": 30}),
            "daily_activity": {"2024-01-15": {"dialogs": 2, "messages": 40}},
            "dialogs_by_length": [("Dialog 1", "test-project", 60)],
        }

        result = cursor_chronicle.format_statistics(sample_stats)

        self.assertIn("USAGE STATISTICS", result)
        self.assertIn("SUMMARY", result)
        self.assertIn("Total dialogs:", result)
        self.assertIn("5", result)
        self.assertIn("PROJECT ACTIVITY", result)
        self.assertIn("test-project", result)

    def test_format_statistics_shows_coding_days(self):
        """Test that format_statistics shows coding days percentage."""
        sample_stats = {
            "period_start": datetime(2024, 1, 1),
            "period_end": datetime(2024, 1, 11),
            "total_dialogs": 5,
            "total_messages": 100,
            "user_messages": 30,
            "ai_messages": 70,
            "tool_calls": 50,
            "thinking_bubbles": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_thinking_time_ms": 0,
            "projects": {},
            "tool_usage": Counter(),
            "daily_activity": {"2024-01-02": {"dialogs": 2, "messages": 40}, "2024-01-05": {"dialogs": 1, "messages": 30}, "2024-01-08": {"dialogs": 2, "messages": 30}},
            "dialogs_by_length": [],
        }

        result = cursor_chronicle.format_statistics(sample_stats)

        self.assertIn("Coding days:", result)
        self.assertIn("3/10", result)
        self.assertIn("30%", result)

    def test_format_statistics_coding_days_without_dates(self):
        """Test coding days display when no period dates."""
        sample_stats = {
            "period_start": None,
            "period_end": None,
            "total_dialogs": 5,
            "total_messages": 100,
            "user_messages": 30,
            "ai_messages": 70,
            "tool_calls": 50,
            "thinking_bubbles": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_thinking_time_ms": 0,
            "projects": {},
            "tool_usage": Counter(),
            "daily_activity": {"2024-01-02": {"dialogs": 2, "messages": 40}, "2024-01-05": {"dialogs": 1, "messages": 30}},
            "dialogs_by_length": [],
        }

        result = cursor_chronicle.format_statistics(sample_stats)

        self.assertIn("Coding days:", result)
        self.assertIn("2", result)

    def test_coding_days_month_calculation(self):
        """Test that coding days correctly calculates month boundaries."""
        sample_stats = {
            "period_start": datetime(2025, 5, 1),
            "period_end": datetime(2025, 6, 1),
            "total_dialogs": 10,
            "total_messages": 100,
            "user_messages": 30,
            "ai_messages": 70,
            "tool_calls": 50,
            "thinking_bubbles": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_thinking_time_ms": 0,
            "projects": {},
            "tool_usage": Counter(),
            "daily_activity": {f"2025-05-{i:02d}": {"dialogs": 1, "messages": 5} for i in range(1, 28)},
            "dialogs_by_length": [],
        }

        result = cursor_chronicle.format_statistics(sample_stats)

        self.assertIn("27/31", result)
        self.assertNotIn("/32", result)

    def test_format_statistics_no_tokens(self):
        """Test formatting stats without tokens."""
        stats = {
            "period_start": datetime(2024, 1, 1),
            "period_end": datetime(2024, 1, 31),
            "total_dialogs": 5,
            "total_messages": 100,
            "user_messages": 30,
            "ai_messages": 70,
            "tool_calls": 0,
            "thinking_bubbles": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_thinking_time_ms": 0,
            "projects": {},
            "tool_usage": Counter(),
            "daily_activity": {},
            "dialogs_by_length": [],
        }

        result = cursor_chronicle.format_statistics(stats)
        self.assertIn("Total dialogs:", result)
        self.assertNotIn("TOKEN USAGE", result)

    def test_format_statistics_max_days_limit(self):
        """Test daily activity is limited by max_days."""
        daily_activity = {f"2024-01-{i:02d}": {"dialogs": 1, "messages": 5} for i in range(1, 25)}

        stats = {
            "period_start": datetime(2024, 1, 1),
            "period_end": datetime(2024, 1, 31),
            "total_dialogs": 20,
            "total_messages": 100,
            "user_messages": 30,
            "ai_messages": 70,
            "tool_calls": 0,
            "thinking_bubbles": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_thinking_time_ms": 0,
            "projects": {},
            "tool_usage": Counter(),
            "daily_activity": daily_activity,
            "dialogs_by_length": [],
        }

        result = cursor_chronicle.format_statistics(stats, max_days=5)
        self.assertIn("DAILY ACTIVITY", result)
        self.assertIn("more days", result)

    def test_format_statistics_many_projects(self):
        """Test project activity truncation."""
        projects = {
            f"project{i}": {
                "dialogs": i, "messages": i * 10, "user_messages": i * 3, "ai_messages": i * 7,
                "tool_calls": i, "tokens_in": i * 100, "tokens_out": i * 50, "dialog_names": [],
            }
            for i in range(1, 20)
        }

        stats = {
            "period_start": datetime(2024, 1, 1),
            "period_end": datetime(2024, 1, 31),
            "total_dialogs": 100,
            "total_messages": 1000,
            "user_messages": 300,
            "ai_messages": 700,
            "tool_calls": 50,
            "thinking_bubbles": 0,
            "total_tokens_in": 10000,
            "total_tokens_out": 5000,
            "total_thinking_time_ms": 0,
            "projects": projects,
            "tool_usage": Counter(),
            "daily_activity": {},
            "dialogs_by_length": [],
        }

        result = cursor_chronicle.format_statistics(stats, top_n=5)
        self.assertIn("PROJECT ACTIVITY", result)
        self.assertIn("more projects", result)


class TestShowStatistics(unittest.TestCase):
    """Test show_statistics function output."""

    def test_show_statistics_output(self):
        """Test show_statistics produces output."""
        viewer = cursor_chronicle.CursorChatViewer()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        captured = StringIO()
        sys.stdout = captured
        try:
            cursor_chronicle.show_statistics(viewer, days=1, start_date=start_date, end_date=end_date)
        finally:
            sys.stdout = sys.__stdout__

        output = captured.getvalue()
        self.assertIn("Collecting statistics", output)


if __name__ == "__main__":
    unittest.main()
