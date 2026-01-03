"""
Command-line interface for Cursor Chronicle.
"""

import argparse
from datetime import datetime
from typing import Optional

from .formatters import format_dialog
from .messages import get_dialog_messages
from .statistics import show_statistics
from .viewer import CursorChatViewer


def parse_date(date_str: str) -> datetime:
    """Parse date string in various formats."""
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"Invalid date format: {date_str}. Use YYYY-MM-DD or similar."
    )


def show_dialog(
    viewer: CursorChatViewer,
    project_name: Optional[str] = None,
    dialog_name: Optional[str] = None,
    max_output_lines: int = 1,
):
    """Show dialog content."""
    projects = viewer.get_projects()

    if not projects:
        print("No projects found.")
        return

    project = None
    if project_name:
        for p in projects:
            if project_name.lower() in p["project_name"].lower():
                project = p
                break
        if not project:
            print(f"Project '{project_name}' not found.")
            return
    else:
        project = projects[0]

    composer = None
    if dialog_name:
        for c in project["composers"]:
            c_name = c.get("name", "").lower()
            if dialog_name.lower() in c_name:
                composer = c
                break
        if not composer:
            print(f"Dialog '{dialog_name}' not found in project '{project['project_name']}'.")
            return
    else:
        if project["composers"]:
            composer = max(project["composers"], key=lambda x: x.get("lastUpdatedAt", 0))
        else:
            print(f"No dialogs found in project '{project['project_name']}'.")
            return

    composer_id = composer.get("composerId")
    if not composer_id:
        print("Dialog ID not found.")
        return

    try:
        messages = get_dialog_messages(composer_id)
        if not messages:
            print("No messages found in dialog.")
            return

        dialog_output = format_dialog(
            messages,
            composer.get("name", "Untitled"),
            project["project_name"],
            max_output_lines,
        )
        print(dialog_output)

    except Exception as e:
        print(f"Error reading dialog: {e}")


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Cursor Chronicle - View Cursor IDE chat history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-projects              # List all projects
  %(prog)s --list-dialogs myproject     # List dialogs in project
  %(prog)s --list-all                   # List all dialogs (by creation date, oldest first)
  %(prog)s --list-all --desc            # List all dialogs (newest first)
  %(prog)s --list-all --updated         # Sort/filter by last updated date
  %(prog)s --list-all --from 2024-01-01 # Dialogs created after date
  %(prog)s --list-all -p myproject      # All dialogs filtered by project
  %(prog)s -p myproject -d "my chat"    # Show specific dialog
  %(prog)s --stats                      # Statistics for last 30 days
  %(prog)s --stats --days 7             # Statistics for last 7 days
  %(prog)s --stats --from 2024-01-01    # Statistics from specific date
  %(prog)s --stats -p myproject         # Statistics for specific project
        """,
    )

    parser.add_argument("--project", "-p", help="Project name (partial match supported)")
    parser.add_argument("--dialog", "-d", help="Dialog name (partial match supported)")
    parser.add_argument("--list-projects", action="store_true", help="Show list of projects")
    parser.add_argument("--list-dialogs", help="Show list of dialogs for project")
    parser.add_argument("--list-all", action="store_true", help="List all dialogs")
    parser.add_argument("--from", dest="start_date", type=parse_date, help="Filter after date")
    parser.add_argument("--before", "--to", dest="end_date", type=parse_date, help="Filter before date")
    parser.add_argument("--limit", type=int, default=50, help="Maximum dialogs (default: 50)")
    parser.add_argument("--sort", choices=["date", "name", "project"], default="date", help="Sort by")
    parser.add_argument("--desc", action="store_true", help="Sort descending")
    parser.add_argument("--updated", action="store_true", help="Use last updated date")
    parser.add_argument("--max-output-lines", type=int, default=1, help="Max lines for tool outputs")
    parser.add_argument("--stats", action="store_true", help="Show usage statistics")
    parser.add_argument("--days", type=int, default=30, help="Days for statistics (default: 30)")
    parser.add_argument("--top", type=int, default=10, help="Top items in rankings (default: 10)")

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    viewer = CursorChatViewer()

    if args.list_projects:
        viewer.list_projects()
    elif args.list_dialogs:
        viewer.list_dialogs(args.list_dialogs)
    elif args.list_all:
        viewer.list_all_dialogs(
            start_date=args.start_date,
            end_date=args.end_date,
            project_filter=args.project,
            limit=args.limit,
            sort_by=args.sort,
            sort_desc=args.desc,
            use_updated=args.updated,
        )
    elif args.stats:
        show_statistics(
            viewer,
            days=args.days,
            start_date=args.start_date,
            end_date=args.end_date,
            project_filter=args.project,
            top_n=args.top,
        )
    else:
        show_dialog(viewer, args.project, args.dialog, args.max_output_lines)


if __name__ == "__main__":
    main()
