# -*- coding: utf-8 -*-
"""Data models for C Drive Scanner application."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ActionType(Enum):
    DELETE = "delete"       # Red - safe to delete
    MIGRATE = "migrate"     # Green - can migrate to other drive
    BOTH = "both"           # Orange - delete or migrate
    SYSTEM = "system"       # Gray - system files, proceed with caution
    INFO = "info"           # Neutral


@dataclass
class ScanItem:
    """A single scannable entity (file or directory)."""
    path: str                          # Absolute path
    name: str                          # Display name
    size_bytes: int                    # Size in bytes
    category: str = ""                 # e.g. "系统文件", "微信/通讯软件"
    description: str = ""              # Human-readable description
    suggested_action: str = ""         # e.g. "迁移到D盘"
    action_type: ActionType = ActionType.INFO
    notes: str = ""                    # Detailed operation notes
    num_files: int = 0                 # File count (for directories)
    num_subdirs: int = 0               # Subdirectory count

    @property
    def size_display(self) -> str:
        """Human readable size string."""
        if self.size_bytes == 0:
            return "0"
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(self.size_bytes)
        unit_idx = 0
        while size >= 1024 and unit_idx < len(units) - 1:
            size /= 1024
            unit_idx += 1
        if unit_idx == 0:
            return f"{int(size)}{units[unit_idx]}"
        return f"{size:.1f}{units[unit_idx]}"


@dataclass
class ProgressMessage:
    """Emitted by scanner thread to UI via queue."""
    phase: str = ""                         # "Phase 1/4: Known paths"
    current_path: str = ""                  # Currently scanning path
    percent: float = 0.0                    # 0.0 to 100.0
    items_found: int = 0
    message_type: str = "progress"          # "progress", "item_found", "phase_complete",
                                            # "scan_complete", "error", "cancelled"
    item: Optional[ScanItem] = None         # Populated for "item_found"
    error_message: str = ""


@dataclass
class ScanResult:
    """Final container of all scan data."""
    drive: str = "C:"
    total_drive_bytes: int = 0
    used_drive_bytes: int = 0
    free_drive_bytes: int = 0
    total_scanned_bytes: int = 0
    items: List[ScanItem] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    scan_duration_seconds: float = 0.0
    username: str = ""

    @property
    def total_drive_display(self) -> str:
        return self._format_bytes(self.total_drive_bytes)

    @property
    def used_drive_display(self) -> str:
        return self._format_bytes(self.used_drive_bytes)

    @property
    def free_drive_display(self) -> str:
        return self._format_bytes(self.free_drive_bytes)

    @property
    def used_percent(self) -> float:
        if self.total_drive_bytes > 0:
            return (self.used_drive_bytes / self.total_drive_bytes) * 100
        return 0.0

    @staticmethod
    def _format_bytes(b: int) -> str:
        if b == 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(b)
        unit_idx = 0
        while size >= 1024 and unit_idx < len(units) - 1:
            size /= 1024
            unit_idx += 1
        if unit_idx == 0:
            return f"{int(size)} {units[unit_idx]}"
        return f"{size:.1f} {units[unit_idx]}"
