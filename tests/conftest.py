"""
Shared test fixtures and utilities for cursor_chronicle tests.
"""

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import cursor_chronicle


@pytest.fixture
def viewer():
    """Create a CursorChatViewer instance."""
    return cursor_chronicle.CursorChatViewer()


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.vscdb', delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE cursorDiskKV (key TEXT, value TEXT)')
    conn.commit()
    conn.close()

    yield db_path

    os.unlink(db_path)


def create_composer_data(composer_id, bubble_ids):
    """Helper to create composer data."""
    return {
        "fullConversationHeadersOnly": [
            {"bubbleId": bid} for bid in bubble_ids
        ]
    }


def insert_bubble(db_path, composer_id, bubble_id, bubble_data):
    """Helper to insert a bubble into database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO cursorDiskKV VALUES (?, ?)",
        (f"bubbleId:{composer_id}:{bubble_id}", json.dumps(bubble_data))
    )
    conn.commit()
    conn.close()


def insert_composer(db_path, composer_id, composer_data):
    """Helper to insert composer data into database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO cursorDiskKV VALUES (?, ?)",
        (f"composerData:{composer_id}", json.dumps(composer_data))
    )
    conn.commit()
    conn.close()
