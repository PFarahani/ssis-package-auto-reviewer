import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from pathlib import Path
from typing import Optional
import logging
from gui.github_theme import GitHubTheme
from config.constants import SSIS_FILE_TYPES, SQL_FILE_TYPES, ICON_PATH


class FileDialog:
    """Handles GUI operations in a single main window."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.root = self._initialize_root()
        GitHubTheme(self.root)
        GitHubTheme.apply_layout(self.root)
        self.package_type = "DIM"
        self.sql_path: Optional[Path] = None
        self.ssis_path: Optional[Path] = None
        self.log_level = "WARNING"
        self._create_widgets()
        self.root.mainloop()

    def _initialize_root(self) -> tk.Tk:
        """Create and configure the root Tkinter window."""
        root = tk.Tk()
        root.title("Auto Review Configuration")
        self._set_window_icon(root)
        return root

    def _set_window_icon(self, window: tk.Tk) -> None:
        """Set the application window icon."""
        try:
            window.iconbitmap(str(ICON_PATH))
        except Exception as e:
            self.logger.error(f"Failed to set window icon: {str(e)}")

    def _create_widgets(self) -> None:
        """Create all UI widgets with GitHub-style layout."""
        # Create main container frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(padx=24, pady=24, fill="both", expand=True)

        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=3,
                          pady=(0, 16), sticky="ew")
        ttk.Label(header_frame,
                  text="SSIS Package Auto Review",
                  font=("Segoe UI", 14, "bold")
                  ).pack(anchor="w")

        # Package Type
        ttk.Label(main_frame, text="Package Type").grid(
            row=1, column=0, sticky="w", pady=4)
        self.pkg_combobox = ttk.Combobox(
            main_frame, values=["DIM", "FACT"], state="readonly")
        self.pkg_combobox.current(0)
        self.pkg_combobox.grid(
            row=1, column=1, columnspan=2, sticky="ew", pady=4)

        # SQL File
        ttk.Label(main_frame, text="SQL File").grid(
            row=2, column=0, sticky="w", pady=4)
        self.sql_entry = ttk.Entry(main_frame, width=40)
        self.sql_entry.grid(row=2, column=1, sticky="ew", pady=4, padx=(0, 4))
        ttk.Button(
            main_frame,
            text="...",
            style="Browse.TButton",
            command=self._browse_sql,
            width=3
        ).grid(row=2, column=2, pady=4, sticky="e")

        # SSIS File
        ttk.Label(main_frame, text="SSIS File").grid(
            row=3, column=0, sticky="w", pady=4)
        self.ssis_entry = ttk.Entry(main_frame, width=40)
        self.ssis_entry.grid(row=3, column=1, sticky="ew", pady=4, padx=(0, 4))
        ttk.Button(
            main_frame,
            text="...",
            style="Browse.TButton",
            command=self._browse_ssis,
            width=3
        ).grid(row=3, column=2, pady=4, sticky="e")

        # Log Level
        ttk.Label(main_frame, text="Log Level").grid(
            row=4, column=0, sticky="w", pady=4)
        self.log_combobox = ttk.Combobox(
            main_frame, values=["INFO", "WARNING", "DEBUG"], state="readonly")
        self.log_combobox.current(1)
        self.log_combobox.grid(
            row=4, column=1, columnspan=2, sticky="ew", pady=4)

        # Submit Button
        submit_frame = ttk.Frame(main_frame)
        submit_frame.grid(row=5, column=0, columnspan=3, pady=16)
        ttk.Button(submit_frame, text="Run Analysis",
                   style="Accent.TButton", command=self._on_submit).pack()

        # Configure grid weights
        # More weight for input columns
        main_frame.columnconfigure(1, weight=3)
        main_frame.columnconfigure(2, weight=0)
        main_frame.rowconfigure(5, weight=1)

        GitHubTheme.apply_layout(main_frame)

    def _browse_sql(self) -> None:
        """Handle SQL file browsing."""
        if path := self._get_file_path("Select SQL File", SQL_FILE_TYPES):
            self.sql_path = path
            self.sql_entry.delete(0, tk.END)
            self.sql_entry.insert(0, str(path))

    def _browse_ssis(self) -> None:
        """Handle SSIS file browsing."""
        if path := self._get_file_path("Select SSIS Package", SSIS_FILE_TYPES):
            self.ssis_path = path
            self.ssis_entry.delete(0, tk.END)
            self.ssis_entry.insert(0, str(path))

    def _get_file_path(self, title: str, file_types) -> Optional[Path]:
        """Generic file selection dialog."""
        try:
            path_str = filedialog.askopenfilename(
                parent=self.root,
                title=title,
                filetypes=file_types
            )
            return Path(path_str) if path_str else None
        except Exception as e:
            self.logger.error(f"File selection failed: {str(e)}")
            return None

    def _on_submit(self) -> None:
        """Handle form submission and set log level."""
        self.package_type = self.pkg_combobox.get()
        self.log_level = self.log_combobox.get()
        self.logger.setLevel(self.log_level.upper())
        self.root.destroy()

    def get_package_type(self) -> str:
        return self.package_type

    def get_ssis_path(self) -> Optional[Path]:
        return self.ssis_path

    def get_sql_path(self) -> Optional[Path]:
        return self.sql_path

    def cleanup(self) -> None:
        try:
            self.root.destroy()
        except tk.TclError:
            pass
