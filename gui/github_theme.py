"""
GitHub-styled theme for Tkinter applications following Primer design system.
https://primer.style/
"""

import tkinter as tk
from tkinter import ttk


class GitHubTheme:
    """Applies GitHub Primer styling to Tkinter widgets."""

    # Color palette (Primer colors)
    COLORS = {
        "bg": "#ffffff",
        "fg": "#24292f",
        "fg-0.75": "#5b5f63",
        "primary": "#0969da",
        "border": "#d0d7de",
        "hover_bg": "#f6f8fa",
        "active_bg": "#0969da",
        "active_bg_tint": "#2178dd",
        "active_bg_shade": "#085fc4",
        "active_fg": "#ffffff",
        "accent_bg": "#2da44e",
        "accent_bg_shade": "#22863a",
        "disabled_bg": "#94a3b8",
        "disabled_fg": "#ffffff",
    }

    # Typography
    FONTS = {
        "default": ("Segoe UI", 10),
        "title": ("Segoe UI", 16, "bold"),
        "label": ("Segoe UI", 10),
        "button": ("Segoe UI", 10, "bold")
    }

    # Spacing
    SPACING = {
        "padding": (6, 8),
        "button_radius": 6,
        "input_padding": (6, 8)
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.style = ttk.Style()
        self._configure_theme()

    def _configure_theme(self) -> None:
        """Configure all widget styles."""
        self._set_base_theme()
        self._configure_labels()
        self._configure_labelframes()
        self._configure_buttons()
        self._configure_accent_buttons()
        self._configure_browse_buttons()
        self._configure_entries()
        self._configure_comboboxes()
        self._configure_frames()
        self._configure_checkbuttons()
        self._configure_text_widgets()

    def _set_base_theme(self) -> None:
        """Set base theme and background."""
        self.root.configure(bg=self.COLORS["bg"])
        self.style.theme_use("clam")

    def _configure_labels(self) -> None:
        """Style labels."""
        self.style.configure("TLabel",
                             font=self.FONTS["label"],
                             background=self.COLORS["bg"],
                             foreground=self.COLORS["fg-0.75"],
                             )

    def _configure_buttons(self) -> None:
        """Style buttons with GitHub's primary color scheme."""
        self.style.configure("TButton",
                             font=self.FONTS["button"],
                             background=self.COLORS["primary"],
                             foreground=self.COLORS['active_fg'],
                             borderwidth=0,
                             padding=self.SPACING["padding"],
                             relief="flat"
                             )
        self.style.map("TButton",
                       background=[
                           ("active", self.COLORS["active_bg_tint"]),
                           ("!active", self.COLORS["active_bg"])
                       ],
                       foreground=[
                           ("active", self.COLORS["active_fg"]),
                           ("!active", self.COLORS["disabled_fg"])
                       ]
                       )

    def _configure_accent_buttons(self) -> None:
        """Style accent buttons."""
        self.style.configure("Accent.TButton",
                             font=self.FONTS["button"],
                             background=self.COLORS['accent_bg'],
                             foreground=self.COLORS['active_fg'],
                             borderwidth=0,
                             padding=self.SPACING["padding"],
                             relief="flat"
                             )
        self.style.map("Accent.TButton",
                       background=[
                           ("active", self.COLORS['accent_bg_shade']),
                           ("disabled", self.COLORS['disabled_bg']),
                       ]
                       )

    def _configure_browse_buttons(self) -> None:
        """Style browse buttons.""" 
        self.style.configure("Browse.TButton",
                             font=self.FONTS["button"],
                             background=self.COLORS["border"],
                             foreground=self.COLORS["fg"],
                             borderwidth=0,
                             padding=(4, 4),
                             relief="flat",
                             width=3
                             )
        self.style.map("Browse.TButton",
                       background=[
                           ("active", self.COLORS["hover_bg"]),
                           ("!active", self.COLORS["border"])
                       ]
                       )

    def _configure_entries(self) -> None:
        """Style entry widgets."""
        self.style.configure("TEntry",
                             fieldbackground=self.COLORS["bg"],
                             foreground=self.COLORS["fg"],
                             bordercolor=self.COLORS["border"],
                             lightcolor=self.COLORS["border"],
                             darkcolor=self.COLORS["border"],
                             padding=(8, 6),
                             insertwidth=2,
                             insertcolor=self.COLORS["fg"]
                             )
        self.style.map("TEntry",
                       bordercolor=[
                           ("focus", self.COLORS["primary"]),
                           ("!focus", self.COLORS["border"])
                       ]
                       )

    def _configure_comboboxes(self) -> None:
        """Style combobox widgets."""
        self.style.configure("TCombobox",
                             selectbackground=self.COLORS["primary"],
                             selectforeground=self.COLORS['active_fg'],
                             fieldbackground=self.COLORS["bg"],
                             background=self.COLORS["bg"],
                             arrowsize=12,
                             arrowcolor=self.COLORS["fg"],
                             padding=(8, 6)
                             )
        self.style.map("TCombobox",
                       fieldbackground=[("readonly", self.COLORS["bg"])],
                       background=[("readonly", self.COLORS["bg"])],
                       bordercolor=[
                           ("focus", self.COLORS["primary"]),
                           ("!focus", self.COLORS["border"])
                       ]
                       )

    def _configure_frames(self) -> None:
        """Style frame widgets."""
        self.style.configure("TFrame",
                             background=self.COLORS["bg"],
                             relief="flat"
                             )

    def _configure_checkbuttons(self) -> None:
        """Style checkbutton widgets."""
        self.style.configure("TCheckbutton",
                            font=self.FONTS["label"],
                            background=self.COLORS["bg"],
                            foreground=self.COLORS["fg"],
                            borderwidth=0,
                            relief="flat",
                            padding=(4, 6)
                            )
        self.style.map("TCheckbutton",
                    background=[("active", self.COLORS["hover_bg"]), 
                                ("!active", self.COLORS["bg"])],
                    foreground=[("active", self.COLORS["fg"]),
                                ("!active", self.COLORS["fg"])],
                    indicatorcolor=[("selected", self.COLORS["primary"]),
                                    ("!selected", self.COLORS["border"])]
                    )

    def _configure_text_widgets(self) -> None:
        """Style text widgets."""
        self.style.configure("Text",
                            background=self.COLORS["bg"],
                            foreground=self.COLORS["fg"],
                            insertbackground=self.COLORS["fg"],
                            selectbackground=self.COLORS["primary"],
                            selectforeground=self.COLORS['active_fg'],
                            relief="solid",
                            borderwidth=1,
                            font=self.FONTS["default"],
                            padding=self.SPACING["input_padding"]
                            )
        self.style.map("Text",
                       bordercolor=[
                           ("focus", self.COLORS["primary"]),
                           ("!focus", self.COLORS["border"])
                       ]
                       )

    def _configure_labelframes(self) -> None:
        """Style ttk.LabelFrame."""
        # Outer box
        self.style.configure(
            "TLabelframe",
            background=self.COLORS["bg"],
            bordercolor=self.COLORS["border"],
            borderwidth=1,
            relief="solid",
            padding=4,
        )
        # The "title" label that sits in the border
        self.style.configure(
            "TLabelframe.Label",
            background=self.COLORS["bg"],
            foreground=self.COLORS["fg-0.75"],
            font=self.FONTS["label"],
            padding=(4, 6),
        )

    @staticmethod
    def apply_layout(widget: ttk.Frame) -> None:
        """Apply GitHub-style spacing and alignment to grids."""
        for child in widget.winfo_children():
            if isinstance(child, (ttk.Label, ttk.Combobox, ttk.Entry)):
                child.grid_configure(padx=12, pady=6, sticky="ew")
            elif isinstance(child, ttk.Button):
                child.grid_configure(padx=12, pady=12, sticky="ew")
