# -*- coding: utf-8 -*-
"""Background scanning engine for C Drive Scanner.

Runs on a background thread, communicates with UI via queue.Queue.
Uses os.scandir() for efficient directory traversal.
Supports cancellation via threading.Event.
"""

import os
import re
import time
import queue
import threading
from typing import List, Optional

from data_model import ScanItem, ProgressMessage, ScanResult, ActionType
from category_rules import classify_path, KNOWN_PATHS

# Size thresholds
LARGE_FILE_THRESHOLD = 500 * 1024 * 1024   # 500 MB
LARGE_DIR_THRESHOLD = 100 * 1024 * 1024     # 100 MB
HUGE_DIR_THRESHOLD = 1 * 1024 * 1024 * 1024 # 1 GB


def get_dir_size(path: str, cancel_event=None, max_depth: int = 10) -> tuple:
    """Calculate total size of a directory recursively.

    Args:
        path: Directory path
        cancel_event: threading.Event for cancellation
        max_depth: Maximum recursion depth

    Returns:
        (total_bytes, file_count, dir_count)
    """
    total = 0
    file_count = 0
    dir_count = 0

    if max_depth <= 0:
        return 0, 0, 0

    try:
        # Use \\?\ prefix for long paths on Windows
        scan_path = f"\\\\?\\{path}" if len(path) > 248 and os.name == "nt" else path
        with os.scandir(scan_path) as it:
            for entry in it:
                if cancel_event and cancel_event.is_set():
                    return total, file_count, dir_count
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                        file_count += 1
                    elif entry.is_dir(follow_symlinks=False):
                        # Skip junctions on Windows
                        if os.name == "nt" and hasattr(entry, "is_junction") and entry.is_junction():
                            continue
                        sub_size, sub_files, sub_dirs = get_dir_size(
                            entry.path, cancel_event, max_depth - 1
                        )
                        total += sub_size
                        file_count += sub_files
                        dir_count += 1 + sub_dirs
                except (PermissionError, FileNotFoundError, OSError):
                    continue
    except (PermissionError, FileNotFoundError, OSError):
        pass

    return total, file_count, dir_count


def get_file_size(path: str) -> int:
    """Get size of a single file."""
    try:
        return os.path.getsize(path)
    except (PermissionError, FileNotFoundError, OSError):
        return 0


class Scanner:
    """Background scanner that walks the C drive and reports findings."""

    def __init__(self, msg_queue: queue.Queue):
        self.queue = msg_queue
        self._cancel_event = threading.Event()
        self.username = os.environ.get("USERNAME", "")
        self.result = ScanResult(username=self.username)
        self._seen_paths = set()  # dedup: track normalized paths

    def cancel(self):
        """Signal the scanner to stop."""
        self._cancel_event.set()

    def _send_progress(self, phase: str, percent: float, current_path: str = "",
                       items_found: int = 0):
        """Send a progress update to the UI."""
        self.queue.put(ProgressMessage(
            message_type="progress",
            phase=phase,
            percent=percent,
            current_path=current_path,
            items_found=items_found,
        ))

    def _add_item(self, item: ScanItem) -> bool:
        """Add an item if not already seen. Returns True if added."""
        norm_path = os.path.normpath(item.path).lower()
        if norm_path in self._seen_paths:
            return False
        self._seen_paths.add(norm_path)
        self.result.items.append(item)
        # Send item to UI
        self.queue.put(ProgressMessage(
            message_type="item_found",
            item=item,
            items_found=len(self.result.items),
            phase=self._current_phase,
        ))
        return True

    def _send_error(self, error_msg: str):
        """Send an error message."""
        self.result.errors.append(error_msg)
        self.queue.put(ProgressMessage(
            message_type="error",
            error_message=error_msg,
        ))

    def _scan_single_path(self, path: str, phase: str) -> Optional[ScanItem]:
        """Scan a single known path and return a classified ScanItem."""
        if self._cancel_event.is_set():
            return None

        if not os.path.exists(path):
            return None

        size = 0
        num_files = 0
        num_dirs = 0

        if os.path.isfile(path):
            size = get_file_size(path)
            num_files = 1
        elif os.path.isdir(path):
            size, num_files, num_dirs = get_dir_size(path, self._cancel_event)

        if size == 0:
            return None

        # Classify the path
        item = classify_path(
            path, size, self.username, num_files, num_dirs
        )

        if item is None:
            # Create a generic item
            item = ScanItem(
                path=path,
                name=os.path.basename(path),
                size_bytes=size,
                category="其他",
                description="未分类的大型文件/目录",
                suggested_action="检查后可处理",
                action_type=ActionType.INFO,
                notes="请手动检查此项目是否可清理或迁移",
                num_files=num_files,
                num_subdirs=num_dirs,
            )

        return item

    def run(self):
        """Main scanner entry point. Runs on background thread."""
        start_time = time.time()
        self._cancel_event.clear()
        self.result = ScanResult(username=self.username)

        # Get drive info
        self._get_drive_info()

        try:
            # Phase 1: Known paths (~25%)
            self._current_phase = "Phase 1/4: 扫描已知路径"
            self._scan_known_paths()

            if self._cancel_event.is_set():
                self._finish_cancelled(start_time)
                return

            # Phase 2: C root shallow scan (~10%)
            self._current_phase = "Phase 2/4: 扫描C盘根目录"
            self._scan_c_root()

            if self._cancel_event.is_set():
                self._finish_cancelled(start_time)
                return

            # Phase 3: User profile deep scan (~40%)
            self._current_phase = "Phase 3/4: 扫描用户目录"
            self._scan_user_profile()

            if self._cancel_event.is_set():
                self._finish_cancelled(start_time)
                return

            # Phase 4: Program Files (~25%)
            self._current_phase = "Phase 4/4: 扫描Program Files"
            self._scan_program_files()

            if self._cancel_event.is_set():
                self._finish_cancelled(start_time)
                return

            # Complete
            self._finish_complete(start_time)

        except Exception as e:
            self._send_error(f"扫描出错: {str(e)}")
            self._finish_complete(start_time)

    def _get_drive_info(self):
        """Get C drive total/used/free space."""
        try:
            import shutil
            usage = shutil.disk_usage("C:\\")
            self.result.total_drive_bytes = usage.total
            self.result.used_drive_bytes = usage.used
            self.result.free_drive_bytes = usage.free
        except Exception:
            self.result.total_drive_bytes = 301 * 1024**3  # fallback
            self.result.used_drive_bytes = 292 * 1024**3
            self.result.free_drive_bytes = 9 * 1024**3

    def _scan_known_paths(self):
        """Phase 1: Scan all known paths from category_rules."""
        known = list(KNOWN_PATHS.keys())
        total = len(known)
        items_found = 0

        for i, template in enumerate(known):
            if self._cancel_event.is_set():
                return

            # Expand user placeholder
            path = template.replace(r"{user}", self.username)
            expanded_template = path.lower()

            # Skip patterns (non-path entries)
            if "{user}" in template and not self.username:
                continue

            percent = 5 + (i / max(total, 1)) * 20  # 5% to 25%

            self._send_progress(
                self._current_phase, percent,
                current_path=path,
                items_found=items_found,
            )

            item = self._scan_single_path(path, self._current_phase)
            if item:
                items_found += 1
                self._add_item(item)

    def _scan_c_root(self):
        """Phase 2: Shallow scan of C root."""
        self._send_progress(self._current_phase, 25, current_path="C:\\")

        try:
            items_found = 0
            entries = list(os.scandir("C:\\"))
            total = len(entries)

            for i, entry in enumerate(entries):
                if self._cancel_event.is_set():
                    return

                percent = 25 + (i / max(total, 1)) * 10

                try:
                    if entry.is_file(follow_symlinks=False):
                        size = get_file_size(entry.path)
                        if size >= LARGE_FILE_THRESHOLD:
                            self._send_progress(
                                self._current_phase, percent,
                                current_path=entry.path,
                                items_found=len(self.result.items),
                            )
                            item = self._scan_single_path(entry.path, self._current_phase)
                            if item:
                                self._add_item(item)
                    elif entry.is_dir(follow_symlinks=False):
                        if hasattr(entry, "is_junction") and entry.is_junction():
                            continue
                        # Only scan top-level dirs for quick size estimate
                        try:
                            size, nf, nd = get_dir_size(entry.path, self._cancel_event, max_depth=2)
                            if size >= HUGE_DIR_THRESHOLD and entry.name.lower() not in ("windows", "users", "program files", "program files (x86)", "programdata"):
                                self._send_progress(
                                    self._current_phase, percent,
                                    current_path=entry.path,
                                    items_found=len(self.result.items),
                                )
                                item = self._scan_single_path(entry.path, self._current_phase)
                                if item:
                                    self._add_item(item)
                        except (PermissionError, OSError):
                            pass
                except (PermissionError, OSError):
                    continue

        except (PermissionError, OSError) as e:
            self._send_error(f"扫描C盘根目录出错: {str(e)}")

    def _scan_user_profile(self):
        """Phase 3: Deep scan of user profile directory."""
        user_dir = f"C:\\Users\\{self.username}"
        if not os.path.isdir(user_dir):
            self._send_error(f"用户目录不存在: {user_dir}")
            return

        self._send_progress(self._current_phase, 35, current_path=user_dir)

        # Key subdirectories to scan deeply
        scan_dirs = [
            (f"{user_dir}\\AppData\\Local", 3),
            (f"{user_dir}\\AppData\\Roaming", 3),
            (f"{user_dir}\\AppData\\LocalLow", 2),
        ]

        if os.path.isdir(f"{user_dir}\\Documents"):
            scan_dirs.append((f"{user_dir}\\Documents", 2))
        if os.path.isdir(f"{user_dir}\\Downloads"):
            scan_dirs.append((f"{user_dir}\\Downloads", 1))

        # Collect all entries
        all_entries = []

        for base_dir, depth in scan_dirs:
            if not os.path.isdir(base_dir):
                continue
            self._send_progress(
                self._current_phase, 37 + scan_dirs.index((base_dir, depth)) * 3,
                current_path=base_dir,
                items_found=len(self.result.items),
            )

            entries = self._collect_large_entries(base_dir, depth, LARGE_DIR_THRESHOLD)
            all_entries.extend(entries)

        # Also check for large files in user root
        self._send_progress(
            self._current_phase, 55,
            current_path=user_dir,
            items_found=len(self.result.items),
        )

        try:
            for entry in os.scandir(user_dir):
                if self._cancel_event.is_set():
                    return
                try:
                    if entry.is_file(follow_symlinks=False):
                        size = get_file_size(entry.path)
                        if size >= LARGE_FILE_THRESHOLD:
                            all_entries.append((entry.path, size, 1, 0))
                except (PermissionError, OSError):
                    pass
        except (PermissionError, OSError):
            pass

        # Classify and emit entries
        total = len(all_entries)
        for i, (path, size, nf, nd) in enumerate(all_entries):
            if self._cancel_event.is_set():
                return
            if any(item.path.lower() == path.lower() for item in self.result.items):
                continue

            percent = 55 + (i / max(total, 1)) * 10
            self._send_progress(
                self._current_phase, percent,
                current_path=path,
                items_found=len(self.result.items),
            )

            item = self._scan_single_path(path, self._current_phase)
            if item:
                self._add_item(item)

    def _collect_large_entries(self, base_path: str, max_depth: int,
                                threshold: int) -> list:
        """Collect entries larger than threshold at given depth.

        Returns list of (path, size_bytes, file_count, dir_count)
        """
        results = []
        if max_depth < 0:
            return results

        try:
            for entry in os.scandir(base_path):
                if self._cancel_event.is_set():
                    return results
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if hasattr(entry, "is_junction") and entry.is_junction():
                            continue
                        size, nf, nd = get_dir_size(
                            entry.path, self._cancel_event, max_depth=4
                        )
                        if size >= threshold:
                            results.append((entry.path, size, nf, nd))
                        elif size >= threshold // 10 and max_depth > 0:
                            # Check one level deeper for moderate dirs
                            results.extend(
                                self._collect_large_entries(
                                    entry.path, max_depth - 1, threshold
                                )
                            )
                    elif entry.is_file(follow_symlinks=False):
                        size = entry.stat(follow_symlinks=False).st_size
                        if size >= threshold // 5:  # 20 MB for files
                            results.append((entry.path, size, 1, 0))
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            pass

        return results

    def _scan_program_files(self):
        """Phase 4: Scan Program Files directories."""
        pf_dirs = [
            "C:\\Program Files",
            "C:\\Program Files (x86)",
        ]

        all_entries = []
        scan_index = 0

        for pf_dir in pf_dirs:
            if not os.path.isdir(pf_dir):
                continue

            self._send_progress(
                self._current_phase, 65 + scan_index * 5,
                current_path=pf_dir,
                items_found=len(self.result.items),
            )

            entries = self._collect_large_entries(pf_dir, 2, HUGE_DIR_THRESHOLD // 2)
            all_entries.extend(entries)
            scan_index += 1

        total = len(all_entries)
        for i, (path, size, nf, nd) in enumerate(all_entries):
            if self._cancel_event.is_set():
                return
            if any(item.path.lower() == path.lower() for item in self.result.items):
                continue

            percent = 75 + (i / max(total, 1)) * 25
            self._send_progress(
                self._current_phase, percent,
                current_path=path,
                items_found=len(self.result.items),
            )

            item = self._scan_single_path(path, self._current_phase)
            if item:
                self._add_item(item)

        # Ensure we reach 100%
        self._send_progress(self._current_phase, 99, items_found=len(self.result.items))

    def _finish_complete(self, start_time: float):
        """Send scan_complete message."""
        self.result.scan_duration_seconds = time.time() - start_time
        self.result.total_scanned_bytes = sum(
            item.size_bytes for item in self.result.items
        )
        self.queue.put(ProgressMessage(
            message_type="scan_complete",
            percent=100.0,
            items_found=len(self.result.items),
            phase="扫描完成",
        ))

    def _finish_cancelled(self, start_time: float):
        """Send cancelled message."""
        self.result.scan_duration_seconds = time.time() - start_time
        self.queue.put(ProgressMessage(
            message_type="cancelled",
            percent=0.0,
            items_found=len(self.result.items),
            phase="扫描已取消",
        ))
