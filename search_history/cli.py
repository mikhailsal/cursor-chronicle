"""
Command-line interface for search_history.
"""

import argparse
from datetime import datetime

from .formatters import format_full_dialog, format_search_results
from .searcher import CursorHistorySearch


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
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
    parser.add_argument("--project", "-p", help="Filter by project name")
    parser.add_argument("--case-sensitive", "-c", action="store_true", help="Case sensitive")
    parser.add_argument("--limit", "-l", type=int, default=50, help="Max results (default: 50)")
    parser.add_argument("--show-context", "-x", action="store_true", help="Show surrounding messages")
    parser.add_argument("--context-size", type=int, default=3, help="Context messages (default: 3)")
    parser.add_argument("--show-dialog", "-d", metavar="COMPOSER_ID", help="Show full dialog")
    parser.add_argument("--list-dialogs", action="store_true", help="List dialogs with match counts")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show progress")

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    searcher = CursorHistorySearch()

    if args.show_dialog:
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
            output = format_full_dialog(
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

    results = searcher.search_all(
        args.query,
        case_sensitive=args.case_sensitive,
        project_filter=args.project,
        limit=args.limit,
        verbose=args.verbose,
    )

    if args.list_dialogs:
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
        output = format_search_results(
            results,
            args.query,
            searcher,
            show_context=args.show_context,
            context_size=args.context_size,
        )
        print(output)


if __name__ == "__main__":
    main()
