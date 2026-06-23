# -*- coding: utf-8 -*-
"""Results panel with TreeView and detail pane."""

import os
import subprocess
import tkinter as tk
from tkinter import ttk
from typing import List, Dict

from data_model import ScanItem, ScanResult, ActionType


class ResultsPanel(ttk.Frame):
    """Right side: TreeView showing categorized scan results + detail pane."""

    def __init__(self, parent, colors: dict):
        super().__init__(parent)
        self.colors = colors
        self.items: List[ScanItem] = []
        self._item_map: Dict[str, ScanItem] = {}  # iid -> ScanItem
        self._sort_column = "size"
        self._sort_reverse = True

        self._build_ui()

    def _build_ui(self):
        # Horizontal paned window for tree + detail
        pw = ttk.PanedWindow(self, orient="horizontal")
        pw.pack(fill="both", expand=True)

        # --- Tree frame ---
        tree_frame = ttk.Frame(pw)
        pw.add(tree_frame, weight=3)

        # Treeview
        columns = ("size", "category", "action")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="tree headings",
            selectmode="browse",
        )
        self.tree.heading("#0", text="文件/目录名称", anchor="w")
        self.tree.heading("size", text="大小", anchor="e",
                          command=lambda: self._sort_by("size"))
        self.tree.heading("category", text="类别", anchor="w")
        self.tree.heading("action", text="建议操作", anchor="w")

        self.tree.column("#0", width=280, minwidth=150)
        self.tree.column("size", width=90, anchor="e", minwidth=60)
        self.tree.column("category", width=120, anchor="w", minwidth=80)
        self.tree.column("action", width=120, anchor="w", minwidth=80)

        # Scrollbar
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical",
                                     command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll.grid(row=0, column=1, sticky="ns")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # Bind selection
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        # Bind right-click
        self.tree.bind("<Button-3>", self._on_right_click)

        # --- Detail frame ---
        detail_frame = ttk.LabelFrame(pw, text="详细信息")
        pw.add(detail_frame, weight=2)

        self.detail_text = tk.Text(
            detail_frame,
            wrap="word",
            font=("Microsoft YaHei UI", 9),
            borderwidth=0,
            padx=10,
            pady=10,
            state="disabled",
            bg=self.colors["bg"],
            fg=self.colors["fg"],
        )
        self.detail_text.pack(fill="both", expand=True, padx=5, pady=5)

    def clear(self):
        """Clear all items from the tree."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.items.clear()
        self._item_map.clear()
        self._show_detail(None)

    def add_item(self, item: ScanItem):
        """Add a single scan item to the tree."""
        self.items.append(item)

        # Find or create category node
        cat_iid = f"cat_{item.category}"
        if not self.tree.exists(cat_iid):
            self.tree.insert(
                "", "end", iid=cat_iid,
                text=item.category, values=("0", "", ""),
                open=True, tags=("category",)
            )
            self._item_map[cat_iid] = None

        # Update category size
        current_val = self.tree.set(cat_iid, "size")
        current_size = 0
        try:
            current_size = self._parse_size(current_val)
        except ValueError:
            current_size = 0
        new_total = current_size + item.size_bytes
        self.tree.set(cat_iid, "size", self._fmt_size(new_total))

        # Add child item
        item_iid = f"item_{len(self._item_map)}"
        action_tag = item.action_type.value

        self.tree.insert(
            cat_iid, "end", iid=item_iid,
            text=item.name,
            values=(
                item.size_display,
                item.category,
                item.suggested_action,
            ),
            tags=(action_tag,)
        )
        self._item_map[item_iid] = item

    def populate(self, items: List[ScanItem]):
        """Populate tree from a list of ScanItems."""
        self.clear()
        # Sort by category then size
        sorted_items = sorted(items, key=lambda x: (x.category, -x.size_bytes))
        for item in sorted_items:
            self.add_item(item)

    def _on_select(self, event):
        """Handle tree item selection."""
        selection = self.tree.selection()
        if selection:
            item = self._item_map.get(selection[0])
            self._show_detail(item)

    def _on_right_click(self, event):
        """Handle right-click context menu."""
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            item = self._item_map.get(iid)
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(
                label="📋 复制路径",
                command=lambda: self._copy_path(item)
            )
            menu.add_command(
                label="📂 在资源管理器中打开",
                command=lambda: self._open_explorer(item)
            )
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

    def _copy_path(self, item):
        """Copy item path to clipboard."""
        if item:
            self.clipboard_clear()
            self.clipboard_append(item.path)

    def _open_explorer(self, item):
        """Open item location in Windows Explorer."""
        if item and os.path.exists(item.path):
            try:
                if os.path.isfile(item.path):
                    subprocess.Popen(["explorer", "/select,", item.path])
                else:
                    subprocess.Popen(["explorer", item.path])
            except Exception:
                pass

    def _show_detail(self, item: ScanItem = None):
        """Show item details in the detail pane."""
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", "end")

        if item is None:
            self.detail_text.insert("1.0", "选择一个项目查看详细信息")
            self.detail_text.config(state="disabled")
            return

        action_emoji = {
            ActionType.DELETE: "🗑️",
            ActionType.MIGRATE: "📦",
            ActionType.BOTH: "🔄",
            ActionType.SYSTEM: "⚙️",
            ActionType.INFO: "ℹ️",
        }

        lines = [
            f"📛 名称: {item.name}",
            f"📂 路径: {item.path}",
            f"📏 大小: {item.size_display}",
            f"📁 文件数: {item.num_files:,}",
            f"📂 子目录数: {item.num_subdirs:,}",
            f"🏷️ 类别: {item.category}",
            f"{action_emoji.get(item.action_type, '')} 建议操作: {item.suggested_action}",
            "",
            "📝 说明:",
            item.description,
            "",
            "🔧 操作注意事项:",
            item.notes,
        ]

        self.detail_text.insert("1.0", "\n".join(lines))
        self.detail_text.config(state="disabled")

    def _sort_by(self, column: str):
        """Sort tree items by column."""
        if self._sort_column == column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column
            self._sort_reverse = True

        # Re-collect items and re-sort
        if column == "size":
            self.items.sort(key=lambda x: x.size_bytes,
                            reverse=self._sort_reverse)
        elif column == "category":
            self.items.sort(key=lambda x: x.category,
                            reverse=self._sort_reverse)

        self.populate(self.items)

    @staticmethod
    def _parse_size(val: str) -> int:
        """Parse display size string to bytes."""
        if not val:
            return 0
        multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3,
                       "TB": 1024**4}
        val = val.strip().upper()
        for unit, mult in multipliers.items():
            if val.endswith(unit):
                try:
                    return int(float(val[:-len(unit)]) * mult)
                except ValueError:
                    return 0
        try:
            return int(val)
        except ValueError:
            return 0

    @staticmethod
    def _fmt_size(b: int) -> str:
        """Format bytes to human readable string."""
        if b == 0:
            return "0"
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(b)
        unit_idx = 0
        while size >= 1024 and unit_idx < len(units) - 1:
            size /= 1024
            unit_idx += 1
        if unit_idx == 0:
            return f"{int(size)}{units[unit_idx]}"
        return f"{size:.1f}{units[unit_idx]}"
