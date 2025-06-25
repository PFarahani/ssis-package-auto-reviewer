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
        self.pkg_combobox_label = ttk.Label(main_frame, text="Package Type")
        self.pkg_combobox_label.grid(row=1, column=0, sticky="w", pady=4)
        self.pkg_combobox = ttk.Combobox(main_frame, values=["DIM", "FACT"], state="readonly")
        self.pkg_combobox.current(0)
        self.pkg_combobox.grid(row=1, column=1, columnspan=2, sticky="ew", pady=4)

        # Log Level Selection
        self.log_combobox_label = ttk.Label(main_frame, text="Log Level")
        self.log_combobox_label.grid(row=2, column=0, sticky="w", pady=4)
        self.log_combobox = ttk.Combobox(main_frame, values=["INFO", "WARNING", "DEBUG"], state="readonly")
        self.log_combobox.current(1)
        self.log_combobox.grid(row=2, column=1, columnspan=2, sticky="ew", pady=4)

        # SSIS File Selection
        self.ssis_label = ttk.Label(main_frame, text="SSIS File")
        self.ssis_label.grid(row=3, column=0, sticky="w", pady=4)
        self.ssis_entry = ttk.Entry(main_frame, width=40)
        self.ssis_entry.grid(row=3, column=1, sticky="ew", pady=4)
        self.ssis_button = ttk.Button(
            main_frame,
            text="...",
            style="Browse.TButton",
            command=self._browse_ssis,
            width=3
        )
        self.ssis_button.grid(row=3, column=2, pady=4, sticky="e")

        # Generate SQL File Checkbox
        self.generate_sql_var = tk.BooleanVar(value=True)  # Default: Active
        self.generate_sql_checkbox = ttk.Checkbutton(
            main_frame,
            text="Generate SQL File",
            variable=self.generate_sql_var,
            command=self._toggle_sql_entry,
            style="TCheckbutton",
            takefocus=False
        )
        self.generate_sql_checkbox.grid(row=4, column=1, sticky="w", pady=4, padx=(8, 0))

        # SQL File Selection
        self.sql_label = ttk.Label(main_frame, text="Insert Null Record Script", wraplength=80)
        self.sql_label.grid(row=5, column=0, sticky="w", pady=4)
        self.sql_entry = ttk.Entry(main_frame, width=40)
        self.sql_entry.grid(row=5, column=1, sticky="ew", pady=4)
        self.sql_button = ttk.Button(
            main_frame,
            text="...",
            style="Browse.TButton",
            command=self._browse_sql,
            width=3
        )
        self.sql_button.grid(row=5, column=2, sticky="e", pady=4)

        # Submit Button
        submit_frame = ttk.Frame(main_frame)
        submit_frame.grid(row=6, column=0, columnspan=3, pady=16)
        self.run_analysis_button = ttk.Button(submit_frame, text="Run Analysis",
                   style="Accent.TButton", command=self._on_submit)
        self.run_analysis_button.pack()
        self.run_analysis_button.config(state="disabled")

        # Configure grid weights
        # More weight for input columns
        main_frame.columnconfigure(1, weight=3)
        main_frame.columnconfigure(2, weight=0)
        main_frame.rowconfigure(6, weight=1)

        # Apply styling
        GitHubTheme.apply_layout(main_frame)

        # Ensure SQL file selection is correctly initialized
        self._toggle_sql_entry()

    def _browse_sql(self) -> None:
        """Handle SQL file browsing."""
        if path := self._get_file_path("Select SQL File", SQL_FILE_TYPES):
            self.sql_path = path
            self.sql_entry.delete(0, tk.END)
            self.sql_entry.insert(0, str(path))
            self._validate_paths()

    def _browse_ssis(self) -> None:
        """Handle SSIS file browsing."""
        if path := self._get_file_path("Select SSIS Package", SSIS_FILE_TYPES):
            self.ssis_path = path
            self.ssis_entry.delete(0, tk.END)
            self.ssis_entry.insert(0, str(path))
            self._validate_paths()

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
        return self.sql_path if self.generate_sql_var.get() else None

    def cleanup(self) -> None:
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def _toggle_sql_entry(self) -> None:
        """Show or hide SQL file selection based on checkbox state."""
        if self.generate_sql_var.get():
            self.sql_label.grid(row=5, column=0, sticky="w", pady=4)
            self.sql_entry.grid(row=5, column=1, sticky="ew", pady=4)
            self.sql_button.grid(row=5, column=2, sticky="e", pady=4)
        else:
            self.sql_label.grid_remove()
            self.sql_entry.grid_remove()
            self.sql_button.grid_remove()
            self.sql_entry.delete(0, tk.END)

        self._validate_paths()

        # Always update and resize after toggling
        self.root.update_idletasks()
        self.root.geometry(self.root.geometry())

    def _validate_paths(self) -> None:
        """Enable 'Run Analysis' button only when both SQL and SSIS paths are set."""
        if self.ssis_path and (self.sql_path if self.generate_sql_var.get() else True):
            self.run_analysis_button.config(state="normal")
        else:
            self.run_analysis_button.config(state="disabled")
