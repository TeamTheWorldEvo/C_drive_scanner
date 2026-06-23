# -*- coding: utf-8 -*-
"""Main application window."""

import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ui.styles import configure_styles
from ui.scan_panel import ScanPanel
from ui.results_panel import ResultsPanel
from scanner import Scanner
from data_model import ScanResult
from excel_generator import ExcelReportGenerator


class MainWindow(ttk.Frame):
    """Top-level application window."""

    def __init__(self, root: tk.Tk):
        super().__init__(root)
        self.root = root

        # Configure styles
        self.colors = configure_styles()

        # Message queue for scanner communication
        self._msg_queue = queue.Queue()
        self.scanner = Scanner(self._msg_queue)
        self._scan_result: ScanResult = None

        self._build_ui()
        self.pack(fill="both", expand=True)

    def _build_ui(self):
        # --- Menu Bar ---
        self._build_menu()

        # Title label
        title_frame = ttk.Frame(self)
        title_frame.pack(fill="x", padx=10, pady=(10, 0))

        ttk.Label(
            title_frame,
            text="C盘清理分析工具",
            style="Heading.TLabel"
        ).pack(side="left")

        ttk.Label(
            title_frame,
            text="只做扫描分析，不会执行任何删除或迁移操作",
            style="Status.TLabel"
        ).pack(side="right")

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=10, pady=5)

        # Scan panel (progress + buttons)
        self.scan_panel = ScanPanel(
            self,
            on_start=self._start_scan,
            on_stop=self._stop_scan,
            on_export=self._export_excel,
        )
        self.scan_panel.pack(fill="x")

        # Results panel (tree + detail)
        self.results_panel = ResultsPanel(self, self.colors)
        self.results_panel.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        # Status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.lbl_drive_info = ttk.Label(
            status_frame,
            text="C盘: 准备扫描...",
            style="Status.TLabel"
        )
        self.lbl_drive_info.pack(side="left")

        self.lbl_summary = ttk.Label(
            status_frame,
            text="",
            style="Status.TLabel"
        )
        self.lbl_summary.pack(side="right")

    def _build_menu(self):
        """Create the menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于...", command=self._show_about)

    def _show_about(self):
        """Show the About dialog with disclaimer, contact, and GitHub link."""
        about_text = (
            "C盘清理分析工具 v1.0\n\n"
            "══════════ 免责声明 ══════════\n"
            "本工具仅供系统空间分析使用，仅提供扫描检测\n"
            "与Excel报告生成功能。本工具不会执行任何实\n"
            "际的文件删除或迁移操作。\n\n"
            "用户在使用本工具生成的报告进行任何文件操作\n"
            "（包括但不限于删除、移动、修改文件）时，所\n"
            "产生的一切后果由用户自行承担。开发者不对因\n"
            "使用本工具或根据报告建议操作所造成的任何数\n"
            "据丢失、系统故障或其他损失承担责任。\n\n"
            "请务必在操作前备份重要数据！\n\n"
            "════════ 联系方式 ════════\n"
            "📧 Email: the_world_evo@163.com\n"
            "🔗 GitHub: https://github.com/TeamTheWorldEvo/\n"
            "           C_drive_scanner.git\n\n"
            "════════ 开源协议 ════════\n"
            "本项目采用Apache-2.0许可证开源\n"
        )
        messagebox.showinfo("关于 C盘清理分析工具", about_text)

        # Bind custom events
        self.scan_panel.bind("<<ScanComplete>>", self._on_scan_complete)
        self.scan_panel.bind("<<ScanCancelled>>", self._on_scan_cancelled)

    def _start_scan(self):
        """Start the scanning process."""
        # Update drive info
        import shutil
        try:
            usage = shutil.disk_usage("C:\\")
            used_pct = (usage.used / usage.total) * 100
            self.lbl_drive_info.config(
                text=f"C盘: {usage.total // (1024**3)}G 总容量 | "
                     f"已用 {usage.used // (1024**3)}G ({used_pct:.1f}%) | "
                     f"可用 {usage.free // (1024**3)}G"
            )
        except Exception:
            self.lbl_drive_info.config(text="C盘: 正在扫描...")

        self.results_panel.clear()
        self._msg_queue = queue.Queue()
        self.scanner = Scanner(self._msg_queue)
        self.scan_panel.set_queue(self._msg_queue)
        self.scan_panel.start_polling()

        # Start scanner in background thread
        thread = threading.Thread(target=self.scanner.run, daemon=True)
        thread.start()

    def _stop_scan(self):
        """Stop the scanning process."""
        if self.scanner:
            self.scanner.cancel()
        self.scan_panel.stop_polling()

    def _on_scan_complete(self, event=None):
        """Handle scan completion."""
        self._scan_result = self.scanner.result

        # Populate results
        self.results_panel.populate(self._scan_result.items)

        # Update summary
        total_items = len(self._scan_result.items)
        total_size = self._scan_result.total_scanned_bytes
        est_free = self._estimate_freeable()

        self.lbl_summary.config(
            text=f"发现 {total_items} 项 | "
                 f"扫描到 {self._fmt_size(total_size)} | "
                 f"预计可释放 {est_free}"
        )

        self.lbl_drive_info.config(
            text=f"C盘: {self._fmt_size(self._scan_result.total_drive_bytes)} 总容量 | "
                 f"已用 {self._fmt_size(self._scan_result.used_drive_bytes)} "
                 f"({self._scan_result.used_percent:.1f}%) | "
                 f"扫描耗时 {self._scan_result.scan_duration_seconds:.1f}秒"
        )

        # Enable export
        if total_items > 0:
            self.scan_panel.btn_export.config(state="normal")
            messagebox.showinfo(
                "扫描完成",
                f"扫描完成！\n\n"
                f"发现 {total_items} 个可处理项目\n"
                f"扫描到的总空间: {self._fmt_size(total_size)}\n"
                f"预计可释放: {est_free}\n\n"
                f"请点击「导出Excel报告」保存详细结果。"
            )

    def _on_scan_cancelled(self, event=None):
        """Handle scan cancellation."""
        if self.scanner:
            self._scan_result = self.scanner.result
            if self._scan_result.items:
                self.results_panel.populate(self._scan_result.items)
        self.lbl_summary.config(text="扫描已取消")
        self.lbl_drive_info.config(text="C盘: 扫描已取消")

    def _export_excel(self):
        """Export results to Excel file."""
        if not self._scan_result or not self._scan_result.items:
            messagebox.showwarning("无数据", "还没有扫描结果，请先扫描C盘。")
            return

        file_path = filedialog.asksaveasfilename(
            title="保存Excel报告",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")],
            initialfile="C盘清理分析报告.xlsx",
        )
        if not file_path:
            return

        try:
            ExcelReportGenerator.generate(self._scan_result, file_path)
            messagebox.showinfo(
                "导出成功",
                f"Excel报告已保存到:\n{file_path}\n\n"
                f"包含3个工作表:\n"
                f"  1. C盘清理总览\n"
                f"  2. 可清理迁移详细清单\n"
                f"  3. 操作指南"
            )
        except Exception as e:
            messagebox.showerror("导出失败", f"生成Excel报告时出错:\n{str(e)}")

    def _estimate_freeable(self) -> str:
        """Estimate how much space can be freed."""
        total = 0
        for item in self._scan_result.items:
            if item.action_type.value in ("delete", "migrate", "both"):
                total += item.size_bytes
            elif item.action_type.value == "system":
                total += item.size_bytes // 4  # conservative for system files
        return self._fmt_size(total)

    @staticmethod
    def _fmt_size(b: int) -> str:
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
