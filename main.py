# -*- coding: utf-8 -*-
"""C Drive Scanner - Windows GUI Application

A read-only scanner that analyzes C drive disk usage,
identifies cleanable/migratable files, and generates an Excel report.
"""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def set_dpi_awareness():
    """Enable high-DPI awareness on Windows for crisp text."""
    try:
        import ctypes
        # PROCESS_SYSTEM_DPI_AWARE = 1
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def main():
    set_dpi_awareness()

    import tkinter as tk
    from ui.main_window import MainWindow

    root = tk.Tk()
    root.title("C盘清理分析工具 v1.0")
    root.geometry("1280x820")
    root.minsize(960, 600)

    # Set app icon (optional)
    try:
        # icon_path = os.path.join(os.path.dirname(__file__), "app_icon.ico")
        # if os.path.exists(icon_path):
        #     root.iconbitmap(icon_path)
        pass
    except Exception:
        pass

    app = MainWindow(root)

    # Handle window close
    def on_close():
        if app.scanner:
            app.scanner.cancel()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
