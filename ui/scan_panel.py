# -*- coding: utf-8 -*-
"""Scan control panel with buttons, progress bar, and status."""

import time
import tkinter as tk
from tkinter import ttk

from data_model import ProgressMessage


class ScanPanel(ttk.Frame):
    """Top panel: Start/Stop buttons, progress bar, status labels."""

    def __init__(self, parent, on_start=None, on_stop=None, on_export=None):
        super().__init__(parent)
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_export = on_export
        self._scanning = False
        self._start_time = 0.0
        self._elapsed_job = None
        self._poll_job = None
        self._message_queue = None

        self._build_ui()

    def _build_ui(self):
        # Toolbar frame
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=10, pady=(10, 5))

        self.btn_scan = ttk.Button(
            toolbar, text="🔍 扫描C盘", style="Primary.TButton",
            command=self._do_start
        )
        self.btn_scan.pack(side="left", padx=(0, 5))

        self.btn_stop = ttk.Button(
            toolbar, text="⏹ 停止", style="Danger.TButton",
            command=self._do_stop, state="disabled"
        )
        self.btn_stop.pack(side="left", padx=5)

        self.btn_export = ttk.Button(
            toolbar, text="📊 导出Excel报告",
            command=self._do_export
        )
        self.btn_export.pack(side="left", padx=5)

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=10, pady=5)

        # Progress section
        progress_frame = ttk.Frame(self)
        progress_frame.pack(fill="x", padx=10, pady=5)

        self.progress_bar = ttk.Progressbar(
            progress_frame, mode="determinate", length=100
        )
        self.progress_bar.pack(fill="x")

        # Status labels
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", padx=10, pady=(2, 5))

        self.lbl_phase = ttk.Label(status_frame, text="就绪", style="Phase.TLabel")
        self.lbl_phase.pack(side="left")

        self.lbl_percent = ttk.Label(status_frame, text="0%", style="Status.TLabel")
        self.lbl_percent.pack(side="right", padx=(10, 0))

        self.lbl_items = ttk.Label(status_frame, text="已发现: 0 项", style="Status.TLabel")
        self.lbl_items.pack(side="right", padx=10)

        self.lbl_elapsed = ttk.Label(status_frame, text="耗时: 00:00", style="Status.TLabel")
        self.lbl_elapsed.pack(side="right", padx=10)

        # Current path
        self.lbl_path = ttk.Label(
            self, text="", style="Status.TLabel",
            wraplength=900, anchor="w"
        )
        self.lbl_path.pack(fill="x", padx=10, pady=(0, 5))

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=10, pady=2)

    def set_queue(self, q):
        """Set the message queue and start polling."""
        self._message_queue = q

    def start_polling(self):
        """Start polling the message queue."""
        self._start_time = time.time()
        self._scanning = True
        self.btn_scan.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.progress_bar["value"] = 0
        self._update_elapsed()
        self._poll_queue()

    def stop_polling(self):
        """Stop polling the queue."""
        self._scanning = False
        self.btn_scan.config(state="normal")
        self.btn_stop.config(state="disabled")
        if self._elapsed_job:
            self.after_cancel(self._elapsed_job)
        if self._poll_job:
            self.after_cancel(self._poll_job)

    def _do_start(self):
        if self.on_start:
            self.on_start()

    def _do_stop(self):
        if self.on_stop:
            self.on_stop()

    def _do_export(self):
        if self.on_export:
            self.on_export()

    def _update_elapsed(self):
        if not self._scanning:
            return
        elapsed = int(time.time() - self._start_time)
        mins, secs = divmod(elapsed, 60)
        self.lbl_elapsed.config(text=f"耗时: {mins:02d}:{secs:02d}")
        self._elapsed_job = self.after(500, self._update_elapsed)

    def _poll_queue(self):
        """Poll the message queue and update UI."""
        if not self._scanning:
            return
        if self._message_queue is None:
            self._poll_job = self.after(100, self._poll_queue)
            return

        try:
            while not self._message_queue.empty():
                msg: ProgressMessage = self._message_queue.get_nowait()
                self._handle_message(msg)
        except Exception:
            pass

        if self._scanning:
            self._poll_job = self.after(100, self._poll_queue)

    def _handle_message(self, msg: ProgressMessage):
        """Process a single progress message."""
        if msg.message_type == "progress":
            self.progress_bar["value"] = msg.percent
            self.lbl_percent.config(text=f"{int(msg.percent)}%")
            self.lbl_phase.config(text=msg.phase)
            self.lbl_items.config(text=f"已发现: {msg.items_found} 项")
            self.lbl_path.config(text=msg.current_path)

        elif msg.message_type == "item_found":
            self.lbl_items.config(text=f"已发现: {msg.items_found} 项")
            # Item display is handled by results_panel

        elif msg.message_type == "scan_complete":
            self.stop_polling()
            self.progress_bar["value"] = 100
            self.lbl_percent.config(text="100%")
            self.lbl_phase.config(text="✅ 扫描完成")
            self.lbl_path.config(text="")
            # Notify parent
            self.event_generate("<<ScanComplete>>", when="tail")

        elif msg.message_type == "cancelled":
            self.stop_polling()
            self.progress_bar["value"] = 0
            self.lbl_phase.config(text="⚠ 扫描已取消")
            self.lbl_path.config(text="")
            self.event_generate("<<ScanCancelled>>", when="tail")

        elif msg.message_type == "error":
            self.lbl_phase.config(text=f"⚠ {msg.error_message[:80]}")
