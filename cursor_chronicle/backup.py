"""
Backup and restore Cursor IDE database files.

Creates compressed backups of Cursor IDE data, storing them in a safe location
separate from Cursor's data directory. Supports listing backups and restoring
from a specific backup.

Backup format: .tar.xz
"""

import io
import json
import lzma
import shutil
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .backup_formatters import (
    _format_size,
    format_backup_list,
    format_backup_summary,
    format_restore_summary,
)
from .utils import get_cursor_paths

# Default backup directory
DEFAULT_BACKUP_DIR = Path.home() / ".cursor-chronicle" / "backups"

# Backup filename pattern
BACKUP_PREFIX = "cursor_backup_"
BACKUP_SUFFIX = ".tar.xz"

# Metadata filename inside the archive
BACKUP_META_FILE = "backup_meta.json"

# LZMA compression preset (0-9, 9 = maximum compression)
LZMA_PRESET = 3

# Emit progress callback at most once per this many bytes while compressing.
PROGRESS_UPDATE_INTERVAL_BYTES = 2 * 1024 * 1024

# Re-export formatting functions for backward compatibility
__all__ = [
    "create_backup",
    "list_backups",
    "restore_backup",
    "get_backup_dir",
    "format_backup_summary",
    "format_backup_list",
    "format_restore_summary",
    "_format_size",
]


def get_backup_dir(config: Optional[Dict] = None) -> Path:
    """Get the backup directory path from config or default."""
    if config and "backup_path" in config:
        return Path(config["backup_path"])
    return DEFAULT_BACKUP_DIR


def _collect_cursor_files() -> Tuple[Path, List[Path]]:
    """Collect all Cursor files that need to be backed up."""
    cursor_config_path, _, _ = get_cursor_paths()
    # get_cursor_paths() returns ".../Cursor/User". We back up the entire Cursor
    # directory so restore can recover full IDE state, not only chat DB files.
    cursor_root = cursor_config_path.parent
    if not cursor_root.exists():
        return cursor_root, []

    files_to_backup = []
    for path in cursor_root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        files_to_backup.append(path)

    files_to_backup.sort(key=lambda p: str(p))
    return cursor_root, files_to_backup


def _build_backup_metadata(files: List[Path], base_path: Path) -> Dict:
    """Build metadata dict for the backup archive."""
    file_entries = []
    total_size = 0

    for f in files:
        size = f.stat().st_size
        total_size += size
        try:
            rel = str(f.relative_to(base_path))
        except ValueError:
            rel = str(f)
        file_entries.append(
            {
                "path": rel,
                "size": size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            }
        )

    return {
        "created_at": datetime.now().isoformat(),
        "cursor_base_path": str(base_path),
        "total_files": len(files),
        "total_size_bytes": total_size,
        "files": file_entries,
    }


def _cleanup_partial_backups(backup_dir: Path) -> None:
    """Remove stale partial backup files left from interrupted runs."""
    for partial in backup_dir.glob(f".{BACKUP_PREFIX}*{BACKUP_SUFFIX}.partial"):
        try:
            partial.unlink()
        except OSError:
            # Best-effort cleanup: stale files should never block listing/backup.
            continue


def create_backup(
    backup_dir: Optional[Path] = None,
    progress_callback: Optional[Callable[[Dict], None]] = None,
) -> Dict:
    """Create a compressed backup of all Cursor files."""
    if backup_dir is None:
        backup_dir = DEFAULT_BACKUP_DIR
    backup_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_partial_backups(backup_dir)

    base_path, files = _collect_cursor_files()
    if not files:
        return {
            "backup_path": None,
            "total_files": 0,
            "total_size": 0,
            "compressed_size": 0,
            "compression_ratio": 0.0,
            "created_at": datetime.now().isoformat(),
            "error": "No Cursor files found to backup.",
        }

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = backup_dir / f"{BACKUP_PREFIX}{timestamp}{BACKUP_SUFFIX}"
    tmp_backup_path = backup_dir / f".{backup_path.name}.partial"
    if tmp_backup_path.exists():
        tmp_backup_path.unlink()

    metadata = _build_backup_metadata(files, base_path)
    total_size = metadata["total_size_bytes"]
    total_files = len(files)

    bytes_processed = 0
    last_reported_bytes = 0

    def _report_progress(current: int, file_path: str, force: bool = False) -> None:
        nonlocal last_reported_bytes
        if not progress_callback:
            return
        if total_size > 0:
            percent = int(min(bytes_processed, total_size) * 100 / total_size)
        else:
            percent = 100
        if (
            not force
            and (bytes_processed - last_reported_bytes) < PROGRESS_UPDATE_INTERVAL_BYTES
        ):
            return
        last_reported_bytes = bytes_processed
        progress_callback(
            {
                "current": current,
                "total": total_files,
                "file_path": file_path,
                "percent": percent,
                "bytes_processed": bytes_processed,
                "bytes_total": total_size,
                "phase": "compressing",
            }
        )

    class _ProgressReader:
        def __init__(self, source_file, on_read):
            self._source_file = source_file
            self._on_read = on_read

        def read(self, size: int = -1):
            chunk = self._source_file.read(size)
            if chunk:
                self._on_read(len(chunk))
            return chunk

    try:
        with tarfile.open(str(tmp_backup_path), "w:xz", preset=LZMA_PRESET) as tar:
            meta_bytes = json.dumps(metadata, indent=2, ensure_ascii=False).encode(
                "utf-8"
            )
            meta_info = tarfile.TarInfo(name=BACKUP_META_FILE)
            meta_info.size = len(meta_bytes)
            tar.addfile(meta_info, io.BytesIO(meta_bytes))

            for idx, file_path in enumerate(files, 1):
                try:
                    rel_path = str(file_path.relative_to(base_path))
                except ValueError:
                    rel_path = str(file_path)

                def _on_read(chunk_len: int) -> None:
                    nonlocal bytes_processed
                    bytes_processed += chunk_len
                    _report_progress(current=idx, file_path=rel_path, force=False)

                with file_path.open("rb") as src_file:
                    tar_info = tar.gettarinfo(
                        name=str(file_path),
                        arcname=rel_path,
                        fileobj=src_file,
                    )
                    src_file.seek(0)
                    tar.addfile(
                        tarinfo=tar_info, fileobj=_ProgressReader(src_file, _on_read)
                    )

                # Force a callback at file boundary for many small files.
                _report_progress(current=idx, file_path=rel_path, force=True)

        tmp_backup_path.replace(backup_path)
    except BaseException:
        if tmp_backup_path.exists():
            tmp_backup_path.unlink()
        raise

    compressed_size = backup_path.stat().st_size
    ratio = ((1 - compressed_size / total_size) * 100) if total_size > 0 else 0.0

    return {
        "backup_path": str(backup_path),
        "total_files": total_files,
        "total_size": total_size,
        "compressed_size": compressed_size,
        "compression_ratio": round(ratio, 1),
        "created_at": metadata["created_at"],
    }


def list_backups(backup_dir: Optional[Path] = None) -> List[Dict]:
    """List all available backups, sorted by date (newest first)."""
    if backup_dir is None:
        backup_dir = DEFAULT_BACKUP_DIR
    if not backup_dir.exists():
        return []
    _cleanup_partial_backups(backup_dir)

    backups = []
    for entry in backup_dir.iterdir():
        if not entry.is_file():
            continue
        if not entry.name.startswith(BACKUP_PREFIX) or not entry.name.endswith(
            BACKUP_SUFFIX
        ):
            continue

        backup_info = {
            "filename": entry.name,
            "path": str(entry),
            "size": entry.stat().st_size,
            "created_at": None,
            "metadata": None,
        }

        name_part = entry.name[len(BACKUP_PREFIX) : -len(BACKUP_SUFFIX)]
        try:
            dt = datetime.strptime(name_part, "%Y-%m-%d_%H-%M-%S")
            backup_info["created_at"] = dt.isoformat()
        except ValueError:
            pass

        meta_data = _read_backup_metadata(entry)
        if meta_data:
            backup_info["metadata"] = meta_data
            if not backup_info["created_at"] and "created_at" in meta_data:
                backup_info["created_at"] = meta_data["created_at"]

        backups.append(backup_info)

    backups.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return backups


def _read_backup_metadata(backup_path: Path) -> Optional[Dict]:
    """
    Read backup metadata efficiently from a tar.xz archive.

    `backup_meta.json` is written as the first archive member in create_backup().
    Reading the first member with tar.next() avoids a full archive scan that
    happens with random member lookup on compressed streams.
    """
    try:
        with tarfile.open(str(backup_path), "r:xz") as tar:
            first_member = tar.next()
            if not first_member:
                return None

            # Fast path: expected archive layout produced by create_backup().
            if first_member.name == BACKUP_META_FILE:
                meta_file = tar.extractfile(first_member)
                if not meta_file:
                    return None
                return json.loads(meta_file.read().decode("utf-8"))

            # Fallback for non-standard archives.
            for member in tar:
                if member.name == BACKUP_META_FILE:
                    meta_file = tar.extractfile(member)
                    if not meta_file:
                        return None
                    return json.loads(meta_file.read().decode("utf-8"))
    except (tarfile.TarError, lzma.LZMAError, OSError, json.JSONDecodeError):
        return None

    return None


def _validate_backup(backup_path: Path) -> Tuple[bool, str, Optional[Dict]]:
    """Validate a backup archive before restoration."""
    if not backup_path.exists():
        return False, f"Backup file not found: {backup_path}", None
    if not backup_path.is_file():
        return False, f"Not a file: {backup_path}", None

    try:
        with tarfile.open(str(backup_path), "r:xz") as tar:
            members = tar.getnames()
            if not members:
                return False, "Backup archive is empty.", None

            metadata = None
            if BACKUP_META_FILE in members:
                meta_file = tar.extractfile(BACKUP_META_FILE)
                if meta_file:
                    metadata = json.loads(meta_file.read().decode("utf-8"))

            has_db = any(m.endswith(".vscdb") for m in members)
            if not has_db:
                return False, "Backup contains no database files (.vscdb).", metadata
            return True, "Backup is valid.", metadata

    except (tarfile.TarError, lzma.LZMAError) as e:
        return False, f"Invalid or corrupted backup archive: {e}", None
    except OSError as e:
        return False, f"Cannot read backup file: {e}", None


def restore_backup(
    backup_path: Path,
    create_pre_restore_backup: bool = True,
    backup_dir: Optional[Path] = None,
    progress_callback: Optional[Callable[[Dict], None]] = None,
) -> Dict:
    """Restore Cursor database files from a backup archive."""
    result = {
        "restored_files": 0,
        "pre_restore_backup": None,
        "errors": [],
        "success": False,
    }

    is_valid, message, metadata = _validate_backup(backup_path)
    if not is_valid:
        result["errors"].append(message)
        return result

    cursor_config_path = get_cursor_paths()[0]
    target_base = (
        Path(metadata["cursor_base_path"])
        if metadata and "cursor_base_path" in metadata
        else cursor_config_path
    )

    if create_pre_restore_backup:
        try:
            pre_backup = create_backup(backup_dir=backup_dir)
            if pre_backup.get("backup_path"):
                result["pre_restore_backup"] = pre_backup["backup_path"]
        except Exception as e:
            result["errors"].append(
                f"Warning: Could not create pre-restore backup: {e}"
            )

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            with tarfile.open(str(backup_path), "r:xz") as tar:
                members = [
                    m
                    for m in tar.getmembers()
                    if m.name != BACKUP_META_FILE and not m.name.startswith("..")
                ]
                total = len(members)
                tar.extractall(path=tmpdir, members=members)

                for idx, member in enumerate(members, 1):
                    if member.isdir():
                        continue
                    src = Path(tmpdir) / member.name
                    dst = target_base / member.name
                    try:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(str(src), str(dst))
                        result["restored_files"] += 1
                    except OSError as e:
                        result["errors"].append(f"Failed to restore {member.name}: {e}")

                    if progress_callback:
                        percent = int(idx * 100 / total) if total > 0 else 0
                        progress_callback(
                            {
                                "current": idx,
                                "total": total,
                                "file_path": member.name,
                                "percent": percent,
                            }
                        )

        except (tarfile.TarError, lzma.LZMAError, OSError) as e:
            result["errors"].append(f"Error during extraction: {e}")
            return result

    result["success"] = result["restored_files"] > 0 and not result["errors"]
    return result
