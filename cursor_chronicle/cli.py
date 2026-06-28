"""
Command-line interface for Cursor Chronicle.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .backup import (
    create_backup,
    format_backup_list,
    format_backup_summary,
    format_restore_summary,
    list_backups,
    restore_backup,
)
from .config import ensure_config_exists, get_backup_path, load_config
from .exporter import export_dialogs, show_export_summary
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


def parse_positive_int(value: str) -> int:
    """Parse and validate a positive integer value."""
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(f"Invalid integer value: {value}") from exc

    if parsed <= 0:
        raise argparse.ArgumentTypeError("Value must be a positive integer")
    return parsed


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
            print(
                f"Dialog '{dialog_name}' not found in project '{project['project_name']}'."
            )
            return
    else:
        if project["composers"]:
            composer = max(
                project["composers"], key=lambda x: x.get("lastUpdatedAt", 0)
            )
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
  %(prog)s --export                     # Export all dialogs to Markdown
  %(prog)s --export -p myproject        # Export only specific project
  %(prog)s --export --verbosity 3       # Export with full verbosity
  %(prog)s --export --export-path /path # Export to specific directory
  %(prog)s --backup                     # Create backup of Cursor databases
  %(prog)s --backup --backup-path /path # Backup to specific directory
  %(prog)s --list-backups               # List available backups
  %(prog)s --restore latest             # Restore from latest backup
  %(prog)s --restore backup_file.tar.xz # Restore from specific backup
  %(prog)s --show-config                # Show current configuration
        """,
    )

    # View/filter arguments
    parser.add_argument(
        "--project", "-p", help="Project name (partial match supported)"
    )
    parser.add_argument("--dialog", "-d", help="Dialog name (partial match supported)")
    parser.add_argument(
        "--list-projects", action="store_true", help="Show list of projects"
    )
    parser.add_argument("--list-dialogs", help="Show list of dialogs for project")
    parser.add_argument("--list-all", action="store_true", help="List all dialogs")
    parser.add_argument(
        "--from", dest="start_date", type=parse_date, help="Filter after date"
    )
    parser.add_argument(
        "--before", "--to", dest="end_date", type=parse_date, help="Filter before date"
    )
    parser.add_argument(
        "--limit",
        type=parse_positive_int,
        default=50,
        help="Maximum dialogs (default: 50)",
    )
    parser.add_argument(
        "--sort", choices=["date", "name", "project"], default="date", help="Sort by"
    )
    parser.add_argument("--desc", action="store_true", help="Sort descending")
    parser.add_argument("--updated", action="store_true", help="Use last updated date")
    parser.add_argument(
        "--max-output-lines",
        type=parse_positive_int,
        default=1,
        help="Max lines for tool outputs",
    )
    parser.add_argument("--stats", action="store_true", help="Show usage statistics")
    parser.add_argument(
        "--days",
        type=parse_positive_int,
        default=30,
        help="Days for statistics (default: 30)",
    )
    parser.add_argument(
        "--top",
        type=parse_positive_int,
        default=10,
        help="Top items in rankings (default: 10)",
    )
    # Export arguments
    parser.add_argument(
        "--export", action="store_true", help="Export dialogs to Markdown files"
    )
    parser.add_argument(
        "--export-path", type=str, default=None, help="Override export directory"
    )
    parser.add_argument(
        "--verbosity",
        type=int,
        choices=[1, 2, 3],
        default=None,
        help="Export verbosity: 1=compact, 2=standard, 3=full",
    )
    parser.add_argument(
        "--show-config", action="store_true", help="Show current configuration"
    )
    # Backup arguments
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create compressed backup of Cursor databases",
    )
    parser.add_argument(
        "--backup-path", type=str, default=None, help="Override backup directory"
    )
    parser.add_argument(
        "--list-backups", action="store_true", help="List available backups"
    )
    parser.add_argument(
        "--restore",
        type=str,
        default=None,
        metavar="BACKUP",
        help="Restore from backup ('latest' or filename/path)",
    )
    parser.add_argument(
        "--no-pre-backup", action="store_true", help="Skip safety backup before restore"
    )

    return parser


def _show_config():
    """Display current configuration."""
    config = ensure_config_exists()
    from .config import get_config_path

    print("Current Cursor Chronicle configuration:")
    print("=" * 50)
    print(f"  Config path:  {get_config_path()}")
    print(f"  Export path:  {config.get('export_path', 'not set')}")
    verbosity = config.get("verbosity", 2)
    verbosity_labels = {1: "compact", 2: "standard", 3: "full"}
    print(f"  Verbosity:    {verbosity} ({verbosity_labels.get(verbosity, 'unknown')})")
    print(f"  Backup path:  {config.get('backup_path', 'not set')}")
    print("=" * 50)


def _print_export_progress(info: Dict) -> None:
    """Print export progress inline (overwrites current line)."""
    percent = info["percent"]
    current = info["current"]
    total = info["total"]
    project = info["project_name"]
    status_icon = {"exported": "✅", "skipped": "⏭️", "error": "❌"}.get(
        info["status"], "•"
    )

    # Truncate project name to keep line short
    if len(project) > 30:
        project = project[:27] + "..."

    line = f"\r  [{percent:3d}%] {current}/{total}  {status_icon}  {project}"
    sys.stdout.write(f"{line:<72}")
    sys.stdout.flush()

    if current == total:
        sys.stdout.write("\n")
        sys.stdout.flush()


def _print_backup_progress(info: Dict) -> None:
    """Print backup/restore progress inline."""
    fp = info["file_path"]
    if len(fp) > 40:
        fp = "..." + fp[-37:]
    line = f"\r  [{info['percent']:3d}%] {info['current']}/{info['total']}  {fp}"
    sys.stdout.write(f"{line:<72}")
    sys.stdout.flush()
    if info["current"] == info["total"]:
        sys.stdout.write("\n")
        sys.stdout.flush()


def _resolve_backup_dir(args):
    """Resolve backup directory from args or config."""
    if args.backup_path:
        return Path(args.backup_path)
    return get_backup_path(load_config())


def _run_backup(args):
    """Run the backup command."""
    backup_dir = _resolve_backup_dir(args)
    print("Creating backup of Cursor files...\n")
    result = create_backup(
        backup_dir=backup_dir, progress_callback=_print_backup_progress
    )
    print("\n" + format_backup_summary(result))


def _run_list_backups(args):
    """Run the list-backups command."""
    print(format_backup_list(list_backups(backup_dir=_resolve_backup_dir(args))))


def _run_restore(args):
    """Run the restore command."""
    backup_dir = _resolve_backup_dir(args)
    backup_identifier = args.restore

    if backup_identifier.lower() == "latest":
        backups = list_backups(backup_dir=backup_dir)
        if not backups:
            print(
                "❌ No backups found. Create one first with: cursor-chronicle --backup"
            )
            return
        backup_path = Path(backups[0]["path"])
        print(f"Using latest backup: {backups[0]['filename']}")
    else:
        backup_path = Path(backup_identifier)
        if not backup_path.exists():
            backup_path = backup_dir / backup_identifier
        if not backup_path.exists():
            print(f"❌ Backup not found: {backup_identifier}")
            print(f"   Searched in: {backup_dir}")
            return

    print("\n⚠️  WARNING: This will overwrite your current Cursor database files!")
    print("   Make sure Cursor IDE is closed before restoring.\n")
    if not args.no_pre_backup:
        print("A safety backup will be created before restoring.\n")
    print(f"Restoring from: {backup_path}\n")

    result = restore_backup(
        backup_path=backup_path,
        create_pre_restore_backup=not args.no_pre_backup,
        backup_dir=backup_dir,
        progress_callback=_print_backup_progress,
    )
    print("\n" + format_restore_summary(result))


def _run_export(args, viewer: CursorChatViewer):
    """Run the export command."""
    export_path = Path(args.export_path) if args.export_path else None
    verbosity = args.verbosity

    print("Exporting dialogs to Markdown...")
    print()

    stats = export_dialogs(
        viewer=viewer,
        export_path=export_path,
        verbosity=verbosity,
        project_filter=args.project,
        start_date=args.start_date,
        end_date=args.end_date,
        progress_callback=_print_export_progress,
    )

    summary = show_export_summary(stats)
    print(summary)


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    viewer = CursorChatViewer()

    if args.backup:
        _run_backup(args)
    elif args.list_backups:
        _run_list_backups(args)
    elif args.restore:
        _run_restore(args)
    elif args.list_projects:
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
    elif args.show_config:
        _show_config()
    elif args.export:
        _run_export(args, viewer)
    else:
        show_dialog(viewer, args.project, args.dialog, args.max_output_lines)


if __name__ == "__main__":
    main()
