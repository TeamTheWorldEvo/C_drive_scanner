# -*- coding: utf-8 -*-
"""ttk Style configuration for C Drive Scanner."""

from tkinter import ttk


def configure_styles():
    """Configure ttk styles for a modern Windows look."""
    style = ttk.Style()

    # Use 'vista' theme for native Windows look, fallback to 'clam'
    available = style.theme_names()
    if "vista" in available:
        style.theme_use("vista")
    elif "clam" in available:
        style.theme_use("clam")

    # Colors
    BG = "#F5F5F5"
    FG = "#333333"
    ACCENT = "#2F5496"
    ACCENT_LIGHT = "#4472C4"
    DELETE_BG = "#FFC7CE"
    MIGRATE_BG = "#C6EFCE"
    BOTH_BG = "#FFEB9C"
    SYSTEM_BG = "#D9D9D9"

    # Base styles
    style.configure(".", background=BG, foreground=FG,
                    font=("Microsoft YaHei UI", 9))
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=FG)

    # Heading
    style.configure("Heading.TLabel",
                    font=("Microsoft YaHei UI", 14, "bold"),
                    foreground=ACCENT,
                    background=BG)

    # Status
    style.configure("Status.TLabel",
                    font=("Microsoft YaHei UI", 9),
                    foreground="#666666",
                    background=BG)

    # Phase label
    style.configure("Phase.TLabel",
                    font=("Microsoft YaHei UI", 10, "bold"),
                    foreground=ACCENT_LIGHT,
                    background=BG)

    # Buttons
    style.configure("TButton",
                    padding=(12, 6),
                    font=("Microsoft YaHei UI", 9))
    style.configure("Primary.TButton",
                    font=("Microsoft YaHei UI", 10, "bold"))
    style.configure("Danger.TButton",
                    font=("Microsoft YaHei UI", 9))

    # Progress bar
    style.configure("TProgressbar",
                    thickness=22,
                    troughcolor="#E0E0E0",
                    background=ACCENT)

    # Treeview
    style.configure("Treeview",
                    font=("Microsoft YaHei UI", 9),
                    rowheight=26)
    style.configure("Treeview.Heading",
                    font=("Microsoft YaHei UI", 9, "bold"),
                    background="#E8E8E8")

    # Category row style
    style.configure("Category.Treeview",
                    font=("Microsoft YaHei UI", 10, "bold"),
                    rowheight=30)

    # Labelframe
    style.configure("TLabelframe", background=BG, borderwidth=1, relief="solid")
    style.configure("TLabelframe.Label",
                    font=("Microsoft YaHei UI", 10, "bold"),
                    foreground=ACCENT,
                    background=BG)

    # PanedWindow
    style.configure("TPanedwindow", background="#CCCCCC")

    # Return useful colors for TreeView tags
    return {
        "delete_bg": DELETE_BG,
        "migrate_bg": MIGRATE_BG,
        "both_bg": BOTH_BG,
        "system_bg": SYSTEM_BG,
        "bg": BG,
        "fg": FG,
        "accent": ACCENT,
        "accent_light": ACCENT_LIGHT,
    }
