#!/usr/bin/env python3
"""
Cursor Chronicle Search
Searches through all Cursor IDE chat history for keywords.
"""

import argparse
import json
import re
import signal
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Handle broken pipe gracefully
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


class CursorHistorySearch:
    def __init__(self):
        self.cursor_config_path = Path.home() / ".config" / "Cursor" / "User"
        self.workspace_storage_path = self.cursor_config_path / "workspaceStorage"
        self.global_storage_path = (
            self.cursor_config_path / "globalStorage" / "state.vscdb"
        )

    def get_all_composers(self) -> List[Dict]:
        """Get all composers from all workspaces with project info"""
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
                # Read project information
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

                # Read composer data from database
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

            except Exception as e:
                continue

        return composers

    def search_in_bubble(self, bubble_data: Dict, query: str, case_sensitive: bool = False) -> List[Dict]:
        """Search for query in bubble data, returns list of matches with context"""
        matches = []
        
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(query), flags)

        # Search in text content
        text = bubble_data.get("text", "")
        if text and pattern.search(text):
            matches.append({
                "field": "text",
                "content": text,
                "type": bubble_data.get("type"),
            })

        # Search in tool data
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

        # Search in thinking content
        thinking = bubble_data.get("thinking", {})
        if thinking:
            if isinstance(thinking, dict):
                thinking_text = thinking.get("content", "") or thinking.get("text", "")
            else:
                thinking_text = str(thinking)
            
            if thinking_text and pattern.search(thinking_text):
                matches.append({
                    "field": "thinking",
                    "content": thinking_text,
                })

        return matches

    def search_composer(self, composer_id: str, query: str, case_sensitive: bool = False) -> List[Dict]:
        """Search all bubbles in a composer for query"""
        if not self.global_storage_path.exists():
            return []

        matches = []
        conn = sqlite3.connect(self.global_storage_path)
        cursor = conn.cursor()

        # Get all bubbles for this composer
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

    def search_all_fast(
        self,
        query: str,
        case_sensitive: bool = False,
        project_filter: Optional[str] = None,
        limit: int = 50,
        verbose: bool = False,
    ) -> List[Dict]:
        """Fast search directly in global database"""
        if not self.global_storage_path.exists():
            return []

        all_results = []
        composers = self.get_all_composers()
        
        # Build composer lookup
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

        # Search directly in database with LIKE
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(query), flags)

        # Get all bubble keys for known composers
        cursor.execute(
            """SELECT key, value FROM cursorDiskKV 
            WHERE key LIKE 'bubbleId:%' AND LENGTH(value) > 100"""
        )

        checked = 0
        for key, value in cursor:
            checked += 1
            if checked % 1000 == 0 and verbose:
                print(f"  Checked {checked} messages...", file=__import__('sys').stderr)

            # Extract composer_id from key
            parts = key.split(":")
            if len(parts) < 2:
                continue
            composer_id = parts[1]
            
            # Skip if not in our lookup
            if composer_id not in composer_lookup:
                continue

            # Quick text check before JSON parsing
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

        # Sort by last updated time
        all_results.sort(key=lambda x: x.get("last_updated", 0), reverse=True)
        return all_results[:limit]

    def search_all(
        self,
        query: str,
        case_sensitive: bool = False,
        project_filter: Optional[str] = None,
        limit: int = 50,
        verbose: bool = False,
    ) -> List[Dict]:
        """Search all history for query (uses fast method)"""
        return self.search_all_fast(query, case_sensitive, project_filter, limit, verbose)

    def get_dialog_context(
        self, composer_id: str, bubble_id: str, context_size: int = 5
    ) -> List[Dict]:
        """Get surrounding messages for context"""
        if not self.global_storage_path.exists():
            return []

        conn = sqlite3.connect(self.global_storage_path)
        cursor = conn.cursor()

        # First get composer data for correct order
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

        # Find position of target bubble
        target_index = -1
        for i, bid in enumerate(ordered_bubble_ids):
            if bid == bubble_id:
                target_index = i
                break

        if target_index == -1:
            conn.close()
            return []

        # Get context range
        start = max(0, target_index - context_size)
        end = min(len(ordered_bubble_ids), target_index + context_size + 1)
        context_ids = ordered_bubble_ids[start:end]

        # Fetch bubbles
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
        """Get full dialog by composer ID"""
        if not self.global_storage_path.exists():
            return []

        conn = sqlite3.connect(self.global_storage_path)
        cursor = conn.cursor()

        # First get composer data for correct order
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

        # If no ordered list, fall back to rowid order
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

                # Skip empty messages
                if not text and not tool_data:
                    continue

                message = {
                    "bubble_id": bubble_data.get("bubbleId", ""),
                    "type": bubble_type,
                    "text": text,
                    "tool_data": tool_data,
                }
                messages.append(message)

            except json.JSONDecodeError:
                continue

        return messages

    def format_search_results(
        self,
        results: List[Dict],
        query: str,
        show_context: bool = False,
        context_size: int = 3,
    ) -> str:
        """Format search results for display"""
        if not results:
            return f"No results found for '{query}'"

        output = []
        output.append(f"🔍 Search results for '{query}'")
        output.append(f"   Found {len(results)} match(es)")
        output.append("=" * 60)

        # Group by dialog
        dialogs = {}
        for result in results:
            dialog_key = (result["composer_id"], result["dialog_name"])
            if dialog_key not in dialogs:
                dialogs[dialog_key] = {
                    "project_name": result["project_name"],
                    "folder_path": result["folder_path"],
                    "dialog_name": result["dialog_name"],
                    "composer_id": result["composer_id"],
                    "last_updated": result["last_updated"],
                    "created_at": result["created_at"],
                    "matches": [],
                }
            dialogs[dialog_key]["matches"].append(result)

        for dialog_key, dialog_info in dialogs.items():
            output.append("")
            output.append(f"📁 Project: {dialog_info['project_name']}")
            output.append(f"💬 Dialog: {dialog_info['dialog_name']}")
            
            # Format dates
            if dialog_info["last_updated"]:
                date = datetime.fromtimestamp(dialog_info["last_updated"] / 1000)
                output.append(f"📅 Last updated: {date.strftime('%Y-%m-%d %H:%M')}")
            if dialog_info["created_at"]:
                date = datetime.fromtimestamp(dialog_info["created_at"] / 1000)
                output.append(f"📅 Created: {date.strftime('%Y-%m-%d %H:%M')}")
            
            output.append(f"🔗 Composer ID: {dialog_info['composer_id']}")
            output.append("-" * 40)

            for match in dialog_info["matches"]:
                field = match.get("field", "unknown")
                content = match.get("content", "")
                msg_type = match.get("type")

                # Determine message type icon
                type_icon = "📝"
                if msg_type == 1:
                    type_icon = "👤 USER"
                elif msg_type == 2:
                    type_icon = "🤖 AI"

                if field == "tool_args" or field == "tool_result":
                    type_icon = f"🛠️ Tool: {match.get('tool_name', 'unknown')}"

                output.append(f"   {type_icon}")

                # Highlight and truncate content
                highlighted = self._highlight_query(content, query)
                if len(highlighted) > 500:
                    # Find the query position and show context around it
                    lower_content = content.lower()
                    lower_query = query.lower()
                    pos = lower_content.find(lower_query)
                    if pos != -1:
                        start = max(0, pos - 200)
                        end = min(len(content), pos + len(query) + 200)
                        highlighted = "..." + self._highlight_query(content[start:end], query) + "..."
                    else:
                        highlighted = highlighted[:500] + "..."

                output.append(f"   {highlighted}")
                output.append("")

            if show_context:
                output.append("   📜 CONTEXT:")
                for match in dialog_info["matches"][:1]:  # Show context for first match
                    context = self.get_dialog_context(
                        match["composer_id"],
                        match["bubble_id"],
                        context_size,
                    )
                    for msg in context:
                        icon = "👤" if msg["type"] == 1 else "🤖"
                        if msg["is_target"]:
                            icon = "➡️" + icon
                        text = msg["text"][:200] + "..." if len(msg["text"]) > 200 else msg["text"]
                        output.append(f"      {icon}: {text}")
                output.append("")

        return "\n".join(output)

    def format_full_dialog(self, messages: List[Dict], dialog_name: str, project_name: str) -> str:
        """Format full dialog for display"""
        output = []
        output.append("=" * 60)
        output.append(f"PROJECT: {project_name}")
        output.append(f"DIALOG: {dialog_name}")
        output.append("=" * 60)
        output.append("")

        for message in messages:
            msg_type = message.get("type")
            text = message.get("text", "")
            tool_data = message.get("tool_data")

            if msg_type == 1:
                output.append("👤 USER:")
                if text:
                    output.append(text)
                output.append("-" * 40)
            elif msg_type == 2:
                if tool_data:
                    tool_name = tool_data.get("name", "unknown")
                    status = tool_data.get("status", "unknown")
                    output.append(f"🛠️ TOOL: {tool_name} ({status})")
                    output.append("-" * 40)
                
                if text:
                    output.append("🤖 AI:")
                    output.append(text)
                    output.append("-" * 40)
            else:
                if text:
                    output.append(f"📝 MESSAGE (type {msg_type}):")
                    output.append(text)
                    output.append("-" * 40)

        return "\n".join(output)

    def _highlight_query(self, text: str, query: str) -> str:
        """Highlight query in text using ANSI colors"""
        pattern = re.compile(f"({re.escape(query)})", re.IGNORECASE)
        return pattern.sub(r"\033[1;33m\1\033[0m", text)


def main():
    parser = argparse.ArgumentParser(
        description="Search Cursor IDE chat history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "KiloCode"                     # Search for KiloCode
  %(prog)s "API" --project myproject      # Search in specific project
  %(prog)s "bug" --show-context           # Show surrounding messages
  %(prog)s --show-dialog <composer_id>    # Show full dialog
  %(prog)s --list-matches "error"         # List all matches briefly
        """,
    )
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument(
        "--project", "-p", help="Filter by project name (partial match)"
    )
    parser.add_argument(
        "--case-sensitive", "-c", action="store_true", help="Case sensitive search"
    )
    parser.add_argument(
        "--limit", "-l", type=int, default=50, help="Maximum results (default: 50)"
    )
    parser.add_argument(
        "--show-context", "-x", action="store_true", help="Show surrounding messages"
    )
    parser.add_argument(
        "--context-size", type=int, default=3, help="Context messages count (default: 3)"
    )
    parser.add_argument(
        "--show-dialog", "-d", metavar="COMPOSER_ID", help="Show full dialog by composer ID"
    )
    parser.add_argument(
        "--list-dialogs", action="store_true", help="List all dialogs with match counts"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show progress"
    )

    args = parser.parse_args()

    searcher = CursorHistorySearch()

    if args.show_dialog:
        # Show full dialog
        composers = searcher.get_all_composers()
        composer = None
        for c in composers:
            if c.get("composerId") == args.show_dialog:
                composer = c
                break

        if not composer:
            print(f"Dialog with ID '{args.show_dialog}' not found.")
            return

        messages = searcher.get_full_dialog(args.show_dialog)
        if messages:
            output = searcher.format_full_dialog(
                messages,
                composer.get("name", "Untitled"),
                composer.get("_project_name", "unknown"),
            )
            print(output)
        else:
            print("No messages found in dialog.")
        return

    if not args.query:
        parser.print_help()
        return

    # Perform search
    results = searcher.search_all(
        args.query,
        case_sensitive=args.case_sensitive,
        project_filter=args.project,
        limit=args.limit,
        verbose=args.verbose,
    )

    if args.list_dialogs:
        # List dialogs with match counts
        dialogs = {}
        for result in results:
            key = result["composer_id"]
            if key not in dialogs:
                dialogs[key] = {
                    "project": result["project_name"],
                    "name": result["dialog_name"],
                    "composer_id": key,
                    "last_updated": result["last_updated"],
                    "count": 0,
                }
            dialogs[key]["count"] += 1

        print(f"🔍 Dialogs containing '{args.query}':")
        print("=" * 60)
        for dialog in sorted(dialogs.values(), key=lambda x: x["last_updated"], reverse=True):
            date = datetime.fromtimestamp(dialog["last_updated"] / 1000) if dialog["last_updated"] else None
            date_str = date.strftime("%Y-%m-%d") if date else "unknown"
            print(f"📁 {dialog['project']} / {dialog['name']}")
            print(f"   Matches: {dialog['count']} | Date: {date_str}")
            print(f"   ID: {dialog['composer_id']}")
            print()
    else:
        # Show full results
        output = searcher.format_search_results(
            results,
            args.query,
            show_context=args.show_context,
            context_size=args.context_size,
        )
        print(output)


if __name__ == "__main__":
    main()
