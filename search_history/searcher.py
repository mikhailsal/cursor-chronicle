"""
Core search functionality for Cursor history.
"""

import json
import re
import signal
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

# Handle broken pipe gracefully
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


class CursorHistorySearch:
    """Search through Cursor IDE chat history."""

    def __init__(self):
        self.cursor_config_path = Path.home() / ".config" / "Cursor" / "User"
        self.workspace_storage_path = self.cursor_config_path / "workspaceStorage"
        self.global_storage_path = (
            self.cursor_config_path / "globalStorage" / "state.vscdb"
        )

    def get_all_composers(self) -> List[Dict]:
        """Get all composers from all workspaces with project info."""
        composers = []

        if not self.workspace_storage_path.exists():
            return composers

        for workspace_dir in self.workspace_storage_path.iterdir():
            if not workspace_dir.is_dir():
                continue

            workspace_json = workspace_dir / "workspace.json"
            state_db = workspace_dir / "state.vscdb"

            if not workspace_json.exists() or not state_db.exists():
                continue

            try:
                with open(workspace_json, "r") as f:
                    workspace_data = json.load(f)

                folder_uri = workspace_data.get("folder", "")
                if folder_uri.startswith("file://"):
                    import urllib.parse
                    folder_path = urllib.parse.unquote(folder_uri[7:])
                    project_name = Path(folder_path).name
                else:
                    project_name = folder_uri
                    folder_path = folder_uri

                conn = sqlite3.connect(state_db)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT value FROM ItemTable WHERE key = 'composer.composerData'"
                )
                result = cursor.fetchone()

                if result:
                    composer_data = json.loads(result[0])
                    for comp in composer_data.get("allComposers", []):
                        comp["_project_name"] = project_name
                        comp["_folder_path"] = folder_path
                        comp["_workspace_id"] = workspace_dir.name
                        composers.append(comp)

                conn.close()

            except Exception:
                continue

        return composers

    def search_in_bubble(
        self, bubble_data: Dict, query: str, case_sensitive: bool = False
    ) -> List[Dict]:
        """Search for query in bubble data, returns list of matches."""
        matches = []
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(query), flags)

        text = bubble_data.get("text", "")
        if text and pattern.search(text):
            matches.append({
                "field": "text",
                "content": text,
                "type": bubble_data.get("type"),
            })

        tool_data = bubble_data.get("toolFormerData", {})
        if tool_data:
            raw_args = tool_data.get("rawArgs", "")
            result = tool_data.get("result", "")

            if raw_args and pattern.search(raw_args):
                matches.append({
                    "field": "tool_args",
                    "content": raw_args,
                    "tool_name": tool_data.get("name", "unknown"),
                })

            if result and pattern.search(result):
                matches.append({
                    "field": "tool_result",
                    "content": result,
                    "tool_name": tool_data.get("name", "unknown"),
                })

        thinking = bubble_data.get("thinking", {})
        if thinking:
            if isinstance(thinking, dict):
                thinking_text = thinking.get("content", "") or thinking.get("text", "")
            else:
                thinking_text = str(thinking)

            if thinking_text and pattern.search(thinking_text):
                matches.append({"field": "thinking", "content": thinking_text})

        return matches

    def search_composer(
        self, composer_id: str, query: str, case_sensitive: bool = False
    ) -> List[Dict]:
        """Search all bubbles in a composer for query."""
        if not self.global_storage_path.exists():
            return []

        matches = []
        conn = sqlite3.connect(self.global_storage_path)
        cursor = conn.cursor()

        cursor.execute(
            """SELECT key, value FROM cursorDiskKV 
            WHERE key LIKE ? AND LENGTH(value) > 100""",
            (f"bubbleId:{composer_id}:%",),
        )
        results = cursor.fetchall()
        conn.close()

        for key, value in results:
            try:
                bubble_data = json.loads(value)
                bubble_matches = self.search_in_bubble(bubble_data, query, case_sensitive)

                if bubble_matches:
                    for match in bubble_matches:
                        match["bubble_id"] = bubble_data.get("bubbleId", "")
                        match["composer_id"] = composer_id
                    matches.extend(bubble_matches)

            except json.JSONDecodeError:
                continue

        return matches

    def search_all(
        self,
        query: str,
        case_sensitive: bool = False,
        project_filter: Optional[str] = None,
        limit: int = 50,
        verbose: bool = False,
    ) -> List[Dict]:
        """Search all history for query."""
        if not self.global_storage_path.exists():
            return []

        all_results = []
        composers = self.get_all_composers()

        composer_lookup = {}
        for c in composers:
            cid = c.get("composerId")
            if cid:
                if project_filter and project_filter.lower() not in c.get("_project_name", "").lower():
                    continue
                composer_lookup[cid] = c

        if verbose:
            print(f"Searching {len(composer_lookup)} dialogs...", file=__import__('sys').stderr)

        conn = sqlite3.connect(self.global_storage_path)
        cursor = conn.cursor()

        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(query), flags)

        cursor.execute(
            """SELECT key, value FROM cursorDiskKV 
            WHERE key LIKE 'bubbleId:%' AND LENGTH(value) > 100"""
        )

        checked = 0
        for key, value in cursor:
            checked += 1
            if checked % 1000 == 0 and verbose:
                print(f"  Checked {checked} messages...", file=__import__('sys').stderr)

            parts = key.split(":")
            if len(parts) < 2:
                continue
            composer_id = parts[1]

            if composer_id not in composer_lookup:
                continue

            if not pattern.search(value):
                continue

            try:
                bubble_data = json.loads(value)
                bubble_matches = self.search_in_bubble(bubble_data, query, case_sensitive)

                if bubble_matches:
                    composer = composer_lookup[composer_id]
                    for match in bubble_matches:
                        match["bubble_id"] = bubble_data.get("bubbleId", "")
                        match["composer_id"] = composer_id
                        match["project_name"] = composer.get("_project_name", "unknown")
                        match["folder_path"] = composer.get("_folder_path", "unknown")
                        match["dialog_name"] = composer.get("name", "Untitled")
                        match["last_updated"] = composer.get("lastUpdatedAt", 0)
                        match["created_at"] = composer.get("createdAt", 0)
                        all_results.append(match)

                    if len(all_results) >= limit:
                        break

            except json.JSONDecodeError:
                continue

        conn.close()

        if verbose:
            print(f"  Found {len(all_results)} matches in {checked} messages", file=__import__('sys').stderr)

        all_results.sort(key=lambda x: x.get("last_updated", 0), reverse=True)
        return all_results[:limit]

    def get_dialog_context(
        self, composer_id: str, bubble_id: str, context_size: int = 5
    ) -> List[Dict]:
        """Get surrounding messages for context."""
        if not self.global_storage_path.exists():
            return []

        conn = sqlite3.connect(self.global_storage_path)
        cursor = conn.cursor()

        cursor.execute(
            """SELECT value FROM cursorDiskKV 
            WHERE key = ? AND LENGTH(value) > 100""",
            (f"composerData:{composer_id}",),
        )
        composer_result = cursor.fetchone()

        ordered_bubble_ids = []
        if composer_result:
            try:
                composer_data = json.loads(composer_result[0])
                if "fullConversationHeadersOnly" in composer_data:
                    ordered_bubble_ids = [
                        bubble["bubbleId"]
                        for bubble in composer_data["fullConversationHeadersOnly"]
                    ]
            except json.JSONDecodeError:
                pass

        target_index = -1
        for i, bid in enumerate(ordered_bubble_ids):
            if bid == bubble_id:
                target_index = i
                break

        if target_index == -1:
            conn.close()
            return []

        start = max(0, target_index - context_size)
        end = min(len(ordered_bubble_ids), target_index + context_size + 1)
        context_ids = ordered_bubble_ids[start:end]

        messages = []
        for bid in context_ids:
            cursor.execute(
                """SELECT value FROM cursorDiskKV 
                WHERE key = ? AND LENGTH(value) > 100""",
                (f"bubbleId:{composer_id}:{bid}",),
            )
            result = cursor.fetchone()
            if result:
                try:
                    bubble_data = json.loads(result[0])
                    messages.append({
                        "bubble_id": bid,
                        "type": bubble_data.get("type"),
                        "text": bubble_data.get("text", ""),
                        "is_target": bid == bubble_id,
                    })
                except json.JSONDecodeError:
                    continue

        conn.close()
        return messages

    def get_full_dialog(self, composer_id: str) -> List[Dict]:
        """Get full dialog by composer ID."""
        if not self.global_storage_path.exists():
            return []

        conn = sqlite3.connect(self.global_storage_path)
        cursor = conn.cursor()

        cursor.execute(
            """SELECT value FROM cursorDiskKV 
            WHERE key = ? AND LENGTH(value) > 100""",
            (f"composerData:{composer_id}",),
        )
        composer_result = cursor.fetchone()

        ordered_bubble_ids = []
        if composer_result:
            try:
                composer_data = json.loads(composer_result[0])
                if "fullConversationHeadersOnly" in composer_data:
                    ordered_bubble_ids = [
                        bubble["bubbleId"]
                        for bubble in composer_data["fullConversationHeadersOnly"]
                    ]
            except json.JSONDecodeError:
                pass

        if not ordered_bubble_ids:
            cursor.execute(
                """SELECT key, value FROM cursorDiskKV 
                WHERE key LIKE ? AND LENGTH(value) > 100 
                ORDER BY rowid""",
                (f"bubbleId:{composer_id}:%",),
            )
            results = cursor.fetchall()
        else:
            results = []
            for bid in ordered_bubble_ids:
                cursor.execute(
                    """SELECT key, value FROM cursorDiskKV 
                    WHERE key = ? AND LENGTH(value) > 100""",
                    (f"bubbleId:{composer_id}:{bid}",),
                )
                result = cursor.fetchone()
                if result:
                    results.append(result)

        conn.close()

        messages = []
        for key, value in results:
            try:
                bubble_data = json.loads(value)
                text = bubble_data.get("text", "").strip()
                bubble_type = bubble_data.get("type")
                tool_data = bubble_data.get("toolFormerData")

                if not text and not tool_data:
                    continue

                messages.append({
                    "bubble_id": bubble_data.get("bubbleId", ""),
                    "type": bubble_type,
                    "text": text,
                    "tool_data": tool_data,
                })

            except json.JSONDecodeError:
                continue

        return messages
