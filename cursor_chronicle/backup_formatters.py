"""
Formatting functions for backup/restore output display.
"""

from typing import Dict, List


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def format_backup_summary(result: Dict) -> str:
    """Format backup creation result for display."""
    lines = []
    lines.append("=" * 60)
    lines.append("💾 CURSOR CHRONICLE - BACKUP SUMMARY")
    lines.append("=" * 60)
    lines.append("")

    if result.get("error"):
        lines.append(f"  ❌ {result['error']}")
        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    lines.append(f"  Backup file:       {result['backup_path']}")
    lines.append(f"  Created at:        {result['created_at']}")
    lines.append(f"  Files backed up:   {result['total_files']}")
    lines.append(f"  Original size:     {_format_size(result['total_size'])}")
    lines.append(f"  Compressed size:   {_format_size(result['compressed_size'])}")
    lines.append(f"  Compression ratio: {result['compression_ratio']}%")
    lines.append("")
    lines.append("  ✅ Backup created successfully!")
    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_backup_list(backups: List[Dict]) -> str:
    """Format backup list for display."""
    lines = []
    lines.append("=" * 60)
    lines.append("💾 CURSOR CHRONICLE - AVAILABLE BACKUPS")
    lines.append("=" * 60)
    lines.append("")

    if not backups:
        lines.append("  No backups found.")
        lines.append("")
        lines.append("  Create one with: cursor-chronicle --backup")
        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    for idx, backup in enumerate(backups, 1):
        lines.append(f"  {idx}. {backup['filename']}")
        lines.append(f"     📦 Size: {_format_size(backup['size'])}")

        if backup.get("created_at"):
            lines.append(f"     📅 Created: {backup['created_at']}")

        meta = backup.get("metadata")
        if meta:
            lines.append(f"     📁 Files: {meta.get('total_files', '?')}")
            orig_size = meta.get("total_size_bytes", 0)
            if orig_size:
                lines.append(f"     📏 Original size: {_format_size(orig_size)}")

        lines.append("")

    lines.append(f"  Total: {len(backups)} backup(s)")
    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_restore_summary(result: Dict) -> str:
    """Format restore result for display."""
    lines = []
    lines.append("=" * 60)
    lines.append("♻️  CURSOR CHRONICLE - RESTORE SUMMARY")
    lines.append("=" * 60)
    lines.append("")

    if result.get("pre_restore_backup"):
        lines.append(f"  🔒 Pre-restore backup: {result['pre_restore_backup']}")
        lines.append("")

    lines.append(f"  Files restored: {result['restored_files']}")

    if result["errors"]:
        lines.append("")
        lines.append("  ⚠️  Warnings/Errors:")
        for err in result["errors"]:
            lines.append(f"     • {err}")

    lines.append("")
    if result["success"]:
        lines.append("  ✅ Restore completed successfully!")
        lines.append("")
        lines.append("  ⚠️  Please restart Cursor IDE for changes to take effect.")
    else:
        lines.append("  ❌ Restore failed or completed with errors.")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
