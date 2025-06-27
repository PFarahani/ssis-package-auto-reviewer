import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import scrolledtext
import threading
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
        self.analysis_running = False

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
        main_frame.pack(padx=16, pady=16, fill="both", expand=True)

        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=3,
                          pady=(0, 16), sticky="ew")
        ttk.Label(header_frame,
                  text="SSIS Package Auto Review",
                  font=("Segoe UI", 16, "bold")
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
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=16)
        button_frame.columnconfigure(0, weight=1)

        self.run_analysis_button = ttk.Button(
            button_frame, 
            text="Run Analysis",
            style="Accent.TButton",
            command=self._start_analysis
        )
        self.run_analysis_button.grid(row=0, column=1, padx=(12, 4))
        self.run_analysis_button.config(state="disabled")

        # Close Button
        self.close_button = ttk.Button(
            button_frame,
            text="Close",
            command=self._on_close,
            style="TButton"
        )
        self.close_button.grid(row=0, column=0, padx=(4, 12))

        # Log Viewer Frame
        log_frame = ttk.LabelFrame(main_frame, text="Analysis Logs", style="TLabelframe")
        log_frame.grid(row=7, column=0, columnspan=3, sticky="nsew", padx=12, pady=6)

        # Text widget for logs
        self.log_viewer = scrolledtext.ScrolledText(
            log_frame,
            state='disabled',
            wrap=tk.WORD,
            bg=GitHubTheme.COLORS["bg"],
            fg=GitHubTheme.COLORS["fg"],
            font=("Consolas", 9),
            insertbackground=GitHubTheme.COLORS["fg"],
            relief="solid",
            bd=0,
            padx=8,
            pady=6,
            height=5,
        )
        self.log_viewer.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Configure grid weights
        # More weight for input columns
        main_frame.columnconfigure(1, weight=3)
        main_frame.columnconfigure(2, weight=0)
        main_frame.rowconfigure(6, weight=1)
        main_frame.rowconfigure(7, weight=1)

        # Apply styling
        GitHubTheme.apply_layout(main_frame)

        # Ensure SQL file selection is correctly initialized
        self._toggle_sql_entry()

        # Prevent too much window shrinking
        self.root.update_idletasks()
        min_w = self.root.winfo_width()
        min_h = self.root.winfo_height()
        self.root.minsize(min_w, min_h)

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

        # Custom handler for GUI logging
        gui_handler = GuiLogHandler(self.log_viewer)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        gui_handler.setFormatter(formatter)
        self.logger.addHandler(gui_handler)

        # Notify main.py to start processing
        if hasattr(self, 'analysis_callback'):
            self.analysis_callback()

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

    def _start_analysis(self) -> None:
        """Start analysis in a separate thread."""
        self.analysis_running = True
        self.run_analysis_button.config(state="disabled")
        self.close_button.config(state="disabled")
        self.log_viewer.config(state='normal')
        self.log_viewer.delete(1.0, tk.END)
        self.log_viewer.insert(tk.END, "Starting analysis...\n")
        self.log_viewer.config(state='disabled')
        
        # Start analysis in separate thread
        analysis_thread = threading.Thread(target=self._on_submit, daemon=True)
        analysis_thread.start()
        
        # Check thread status periodically
        self.root.after(100, self._check_analysis_status, analysis_thread)

    def _check_analysis_status(self, thread: threading.Thread) -> None:
        """Check if analysis thread has completed."""
        if thread.is_alive():
            self.root.after(100, self._check_analysis_status, thread)
        else:
            self.analysis_running = False
            self.close_button.config(state="normal")
            self.log_viewer.config(state='normal')
            self.log_viewer.insert(tk.END, "\nAnalysis completed!\n")
            self.log_viewer.config(state='disabled')

    def _on_close(self) -> None:
        """Handle close button click."""
        self.root.destroy()

    def set_analysis_callback(self, callback: callable) -> None:
        """Set callback for analysis start."""
        self.analysis_callback = callback

    def append_log(self, message: str) -> None:
        """Append message to log viewer."""
        self.log_viewer.config(state='normal')
        self.log_viewer.insert(tk.END, message + "\n")
        self.log_viewer.see(tk.END)
        self.log_viewer.config(state='disabled')
        
    def mainloop(self) -> None:
        """Start GUI main loop."""
        self.root.mainloop()

class GuiLogHandler(logging.Handler):
    """Custom logging handler for GUI output."""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        
    def emit(self, record):
        msg = self.format(record)
        self.text_widget.config(state='normal')
        self.text_widget.insert(tk.END, msg + "\n")
        self.text_widget.see(tk.END)
        self.text_widget.config(state='disabled')