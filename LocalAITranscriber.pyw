import os
import sys
import json
import time
import threading
import traceback
import subprocess
import importlib
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ------------------------------------------------------------
# Optional drag-and-drop support
# ------------------------------------------------------------
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except Exception:
    TkinterDnD = None
    DND_FILES = None
    DND_AVAILABLE = False

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

APP_NAME = "LocalAITranscriber"
SUPPORTED_EXTENSIONS = {
    ".mp4", ".mp3", ".wav", ".m4a", ".mov", ".mkv",
    ".webm", ".aac", ".flac", ".ogg", ".wma", ".mpeg", ".mpg"
}

CONTENT_TYPES = {
    "Lecture / Course": (
        "This is a lecture, class, training session, or educational recording. Preserve important terminology, "
        "names, acronyms, numbers, formulas, units, and instructions carefully. Use natural punctuation and "
        "sentence boundaries, but do not summarize or rewrite the speaker's meaning."
    ),
    "Research / Lab / Technical": (
        "This is a technical, scientific, engineering, medical, laboratory, or research recording. Preserve "
        "specialized terminology, abbreviations, measurements, units, product or model names, software names, "
        "and technical language carefully. Do not simplify technical wording."
    ),
    "Meeting / Study Group": (
        "This is a meeting, team discussion, class group, or study-group recording. Preserve decisions, action "
        "items, assignments, names, dates, numbers, and changes of topic accurately while keeping conversational "
        "wording natural."
    ),
    "Interview / Q&A": (
        "This is an interview, question-and-answer session, consultation, or recorded discussion. Preserve "
        "questions and answers accurately, including names, organizations, dates, numbers, and quoted wording "
        "where possible."
    ),
    "Podcast / Conversation": (
        "This is a podcast or conversational recording. Preserve natural conversational phrasing, names, titles, "
        "references, numbers, and topic changes while adding sensible punctuation."
    ),
    "Presentation / Webinar": (
        "This is a presentation, seminar, webinar, conference talk, or formal briefing. Preserve slide terminology, "
        "names, organizations, product names, numbers, dates, and structured points accurately."
    ),
    "Video / Voiceover": (
        "This is video content, narration, a voiceover, demonstration, or recorded explanation. Produce a faithful "
        "transcript with natural punctuation while preserving names, numbers, titles, and important terminology."
    ),
    "General / Other": (
        "Produce a faithful transcript of the recording. Preserve names, numbers, acronyms, and important terms, "
        "and use natural punctuation without summarizing."
    ),
}


# Keep DLL directory handles alive for the life of the process.
CUDA_DLL_HANDLES = []


def _version_key_from_name(name):
    """Return a sortable tuple for names such as v12.8 or v12.6."""
    try:
        raw = name.lower().lstrip("v")
        return tuple(int(part) for part in raw.split("."))
    except Exception:
        return (0,)


def discover_windows_cuda_runtime_dirs():
    """
    Find CUDA 12 and common cuDNN runtime folders on Windows.
    CTranslate2/faster-whisper currently works best with CUDA 12 runtime DLLs.
    """
    if os.name != "nt":
        return []

    candidates = []

    # CUDA Toolkit installs, newest CUDA 12 first.
    cuda_root = Path(os.environ.get(
        "CUDA_PATH_ROOT",
        r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA"
    ))
    if cuda_root.exists():
        versions = [p for p in cuda_root.iterdir() if p.is_dir() and p.name.lower().startswith("v12.")]
        versions.sort(key=lambda p: _version_key_from_name(p.name), reverse=True)
        for version_dir in versions:
            bin_dir = version_dir / "bin"
            if bin_dir.exists():
                candidates.append(bin_dir)

    # Respect CUDA_PATH_V12_* variables if Windows/NVIDIA created them.
    for key, value in os.environ.items():
        if key.upper().startswith("CUDA_PATH_V12") and value:
            bin_dir = Path(value) / "bin"
            if bin_dir.exists():
                candidates.append(bin_dir)

    # Common standalone cuDNN install locations.
    cudnn_roots = [
        Path(r"C:\Program Files\NVIDIA\CUDNN"),
        Path(r"C:\Program Files\NVIDIA Corporation\cuDNN"),
    ]
    for root in cudnn_roots:
        if not root.exists():
            continue
        for path in root.rglob("bin"):
            if path.is_dir():
                candidates.append(path)

    # NVIDIA pip wheels may place runtime DLLs under site-packages\nvidia\...\bin.
    try:
        import site
        site_roots = [Path(p) for p in site.getsitepackages() if p]
        user_site = site.getusersitepackages()
        if user_site:
            site_roots.append(Path(user_site))
        for base in site_roots:
            nvidia_root = base / "nvidia"
            if nvidia_root.exists():
                for path in nvidia_root.rglob("bin"):
                    if path.is_dir():
                        candidates.append(path)
    except Exception:
        pass

    # Stable de-duplication.
    seen = set()
    result = []
    for path in candidates:
        try:
            resolved = str(path.resolve())
        except Exception:
            resolved = str(path)
        key = resolved.lower()
        if key not in seen and os.path.isdir(resolved):
            seen.add(key)
            result.append(resolved)
    return result


def configure_windows_cuda_runtime():
    """
    Put compatible CUDA/cuDNN DLL folders on this process's search path.
    This affects the transcriber only and does not permanently edit Windows PATH.
    """
    dirs = discover_windows_cuda_runtime_dirs()
    if os.name != "nt":
        return dirs

    current_path = os.environ.get("PATH", "")
    existing = [p for p in current_path.split(os.pathsep) if p]
    existing_lower = {p.lower() for p in existing}

    # Prepend in reverse so the first discovered (newest CUDA 12) remains first.
    for directory in reversed(dirs):
        if directory.lower() not in existing_lower:
            current_path = directory + os.pathsep + current_path

    os.environ["PATH"] = current_path

    if hasattr(os, "add_dll_directory"):
        for directory in dirs:
            try:
                CUDA_DLL_HANDLES.append(os.add_dll_directory(directory))
            except Exception:
                pass
    return dirs


def query_nvidia_gpu_name():
    if os.name != "nt":
        return "NVIDIA GPU"
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            creationflags=hidden_process_flags(),
        )
        if result.returncode == 0:
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if lines:
                return lines[0]
    except Exception:
        pass
    return "NVIDIA GPU"



def app_data_dir():
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home())
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


CONFIG_PATH = app_data_dir() / "settings.json"
ERROR_LOG = app_data_dir() / "error.log"


def hidden_process_flags():
    if os.name == "nt":
        return subprocess.CREATE_NO_WINDOW
    return 0


def python_for_pip():
    exe = Path(sys.executable)
    if os.name == "nt" and exe.name.lower() == "pythonw.exe":
        console_python = exe.with_name("python.exe")
        if console_python.exists():
            return str(console_python)
    return sys.executable


def write_error_log(context, exc):
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
            f.write(context + "\n")
            f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except Exception:
        pass


def format_clock(seconds):
    seconds = max(0, int(seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours:
        return f"{hours:02}:{minutes:02}:{secs:02}"
    return f"{minutes:02}:{secs:02}"


def format_srt_time(seconds):
    seconds = max(0.0, float(seconds))
    whole = int(seconds)
    ms = int(round((seconds - whole) * 1000))
    if ms == 1000:
        whole += 1
        ms = 0
    hours = whole // 3600
    minutes = (whole % 3600) // 60
    secs = whole % 60
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


class TranscriptionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Local AI Transcriber")
        self.root.geometry("1180x820")
        self.root.minsize(980, 700)

        self.cuda_runtime_dirs = configure_windows_cuda_runtime()
        self.gpu_name = query_nvidia_gpu_name()
        self.cuda_verified_keys = set()
        self.hardware_test_running = False

        self.settings = self.load_settings()
        self.queue = []
        self.queue_index = 0
        self.queue_tree_to_job = {}
        self.cancel_event = threading.Event()
        self.processing = False
        self.current_output_folder = ""

        self.WhisperModel = None
        self.ctranslate2 = None
        self.loaded_model = None
        self.loaded_model_key = None

        self.configure_theme()
        self.build_ui()
        self.apply_settings_to_ui()
        self.setup_drag_drop()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.root.after(250, self.start_dependency_check)

    # --------------------------------------------------------
    # Settings
    # --------------------------------------------------------
    def load_settings(self):
        defaults = {
            "model": "small",
            "language": "English",
            "hardware": "Auto",
            "content_type": "Lecture / Course",
            "context_notes": "",
            "output_folder": "",
            "export_txt": True,
            "export_timestamped": True,
            "export_srt": True,
            "last_input_folder": "",
        }
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                defaults.update(data)
        except Exception as exc:
            write_error_log("Loading settings", exc)
        return defaults

    def collect_settings(self):
        self.settings.update({
            "model": self.model_var.get(),
            "language": self.language_var.get(),
            "hardware": self.hardware_var.get(),
            "content_type": self.content_type_var.get(),
            "context_notes": self.context_notes.get("1.0", tk.END).strip(),
            "output_folder": self.output_folder_var.get().strip(),
            "export_txt": bool(self.export_txt_var.get()),
            "export_timestamped": bool(self.export_timestamped_var.get()),
            "export_srt": bool(self.export_srt_var.get()),
        })

    def save_settings(self):
        try:
            self.collect_settings()
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as exc:
            write_error_log("Saving settings", exc)

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------
    def configure_theme(self):
        """Apply a clean, consistent desktop theme without changing app behavior."""
        self.root.configure(bg="#f3f5f8")

        style = ttk.Style(self.root)
        available = style.theme_names()
        if os.name == "nt" and "vista" in available:
            style.theme_use("vista")
        elif "clam" in available:
            style.theme_use("clam")

        style.configure("TFrame", font=("Segoe UI", 10))
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 6))
        style.configure("TCheckbutton", font=("Segoe UI", 10))
        style.configure("TEntry", font=("Segoe UI", 10), padding=5)
        style.configure("TCombobox", font=("Segoe UI", 10), padding=4)
        style.configure("TLabelframe", padding=10)
        style.configure("TLabelframe.Label", font=("Segoe UI Semibold", 10))
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=30)
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10))
        style.configure("Primary.TButton", font=("Segoe UI Semibold", 10), padding=(14, 7))
        style.configure("Danger.TButton", font=("Segoe UI Semibold", 10), padding=(14, 7))
        style.configure("Header.TLabel", font=("Segoe UI Semibold", 10))
        style.configure("Muted.TLabel", font=("Segoe UI", 9), foreground="#667085")

    def build_ui(self):
        # Main shell
        outer = ttk.Frame(self.root, padding=(18, 16, 18, 14))
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        # Header
        header = tk.Frame(outer, bg="#172033", height=70)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.columnconfigure(0, weight=1)

        title_wrap = tk.Frame(header, bg="#172033")
        title_wrap.grid(row=0, column=0, sticky="w", padx=18, pady=10)
        tk.Label(
            title_wrap,
            text="Local AI Transcriber",
            font=("Segoe UI Semibold", 20),
            bg="#172033",
            fg="white"
        ).pack(anchor="w")
        tk.Label(
            title_wrap,
            text="Private local speech-to-text for audio and video",
            font=("Segoe UI", 9),
            bg="#172033",
            fg="#cbd5e1"
        ).pack(anchor="w", pady=(1, 0))

        self.engine_status = tk.Label(
            header,
            text="Checking transcription engine...",
            font=("Segoe UI", 9),
            bg="#172033",
            fg="#dbeafe",
            anchor="e"
        )
        self.engine_status.grid(row=0, column=1, sticky="e", padx=18)

        # Setup card
        setup = ttk.LabelFrame(outer, text="Transcription setup", padding=(12, 10))
        setup.grid(row=1, column=0, sticky="ew", pady=(14, 12))
        for col in range(5):
            setup.columnconfigure(col, weight=1 if col < 4 else 0)

        self.model_var = tk.StringVar()
        self.language_var = tk.StringVar()
        self.hardware_var = tk.StringVar()
        self.content_type_var = tk.StringVar()

        def add_field(parent, col, label_text, variable, values, width=20):
            box = ttk.Frame(parent)
            box.grid(row=0, column=col, sticky="ew", padx=(0, 12) if col < 3 else (0, 10))
            box.columnconfigure(0, weight=1)
            ttk.Label(box, text=label_text, style="Header.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
            combo = ttk.Combobox(
                box,
                textvariable=variable,
                values=values,
                state="readonly",
                width=width
            )
            combo.grid(row=1, column=0, sticky="ew")
            return combo

        self.model_combo = add_field(
            setup, 0, "Quality / model", self.model_var,
            ["tiny", "base", "small", "medium", "large-v3"], width=16
        )
        self.language_combo = add_field(
            setup, 1, "Language", self.language_var,
            ["English", "Auto Detect"], width=16
        )
        self.hardware_combo = add_field(
            setup, 2, "Hardware", self.hardware_var,
            ["Auto", "CPU", "NVIDIA GPU"], width=16
        )
        self.content_type_combo = add_field(
            setup, 3, "Recording type", self.content_type_var,
            list(CONTENT_TYPES.keys()), width=26
        )

        self.hardware_test_button = ttk.Button(
            setup,
            text="Test Hardware",
            command=self.start_hardware_test,
            state="disabled"
        )
        self.hardware_test_button.grid(row=0, column=4, sticky="se", padx=(4, 0), pady=(18, 0))

        # Context and output live on one aligned row below the selectors.
        lower_setup = ttk.Frame(setup)
        lower_setup.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(12, 0))
        lower_setup.columnconfigure(0, weight=3)
        lower_setup.columnconfigure(1, weight=2)

        context_card = ttk.Frame(lower_setup)
        context_card.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        context_card.columnconfigure(0, weight=1)
        ttk.Label(context_card, text="Optional context", style="Header.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.context_notes = tk.Text(
            context_card,
            height=3,
            wrap="word",
            font=("Segoe UI", 10),
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=6
        )
        self.context_notes.grid(row=1, column=0, sticky="ew")
        ttk.Label(
            context_card,
            text="Optional names, course or topic, acronyms, company names, or uncommon terms.",
            style="Muted.TLabel"
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))

        output_card = ttk.Frame(lower_setup)
        output_card.grid(row=0, column=1, sticky="nsew")
        output_card.columnconfigure(0, weight=1)
        ttk.Label(output_card, text="Output folder", style="Header.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))

        self.output_folder_var = tk.StringVar()
        self.output_entry = ttk.Entry(output_card, textvariable=self.output_folder_var)
        self.output_entry.grid(row=1, column=0, sticky="ew")
        ttk.Button(output_card, text="Browse", command=self.choose_output_folder).grid(row=1, column=1, padx=(6, 4))
        ttk.Button(output_card, text="Open", command=self.open_output_folder).grid(row=1, column=2, padx=(0, 0))

        self.export_txt_var = tk.BooleanVar(value=True)
        self.export_timestamped_var = tk.BooleanVar(value=True)
        self.export_srt_var = tk.BooleanVar(value=True)
        export_row = ttk.Frame(output_card)
        export_row.grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Checkbutton(export_row, text="TXT", variable=self.export_txt_var).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(export_row, text="Timestamped TXT", variable=self.export_timestamped_var).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(export_row, text="SRT", variable=self.export_srt_var).pack(side="left")
        ttk.Label(
            output_card,
            text="Leave blank to save beside each source file.",
            style="Muted.TLabel"
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))

        # Main work area
        workspace = ttk.Panedwindow(outer, orient="horizontal")
        workspace.grid(row=2, column=0, sticky="nsew")

        # Queue pane
        queue_panel = ttk.Frame(workspace, padding=(0, 0, 8, 0))
        workspace.add(queue_panel, weight=6)
        queue_panel.columnconfigure(0, weight=1)
        queue_panel.rowconfigure(1, weight=1)

        queue_toolbar = ttk.Frame(queue_panel)
        queue_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        ttk.Label(queue_toolbar, text="Queue", font=("Segoe UI Semibold", 12)).pack(side="left")

        toolbar_actions = ttk.Frame(queue_toolbar)
        toolbar_actions.pack(side="right")
        self.add_files_button = ttk.Button(toolbar_actions, text="Add Files", command=self.add_files, state="disabled")
        self.add_files_button.pack(side="left", padx=(0, 5))
        self.add_folder_button = ttk.Button(toolbar_actions, text="Add Folder", command=self.add_folder, state="disabled")
        self.add_folder_button.pack(side="left", padx=5)
        self.remove_button = ttk.Button(toolbar_actions, text="Remove", command=self.remove_selected, state="disabled")
        self.remove_button.pack(side="left", padx=5)
        self.clear_button = ttk.Button(toolbar_actions, text="Clear", command=self.clear_queue, state="disabled")
        self.clear_button.pack(side="left", padx=(5, 0))

        queue_box = ttk.Frame(queue_panel)
        queue_box.grid(row=1, column=0, sticky="nsew")
        queue_box.columnconfigure(0, weight=1)
        queue_box.rowconfigure(0, weight=1)

        columns = ("name", "status", "details")
        self.queue_tree = ttk.Treeview(queue_box, columns=columns, show="headings", selectmode="extended")
        self.queue_tree.heading("name", text="File")
        self.queue_tree.heading("status", text="Status")
        self.queue_tree.heading("details", text="Details")
        self.queue_tree.column("name", width=330, minwidth=200, anchor="w", stretch=True)
        self.queue_tree.column("status", width=100, minwidth=90, anchor="center", stretch=False)
        self.queue_tree.column("details", width=260, minwidth=160, anchor="w", stretch=True)
        self.queue_tree.grid(row=0, column=0, sticky="nsew")

        queue_scroll = ttk.Scrollbar(queue_box, orient="vertical", command=self.queue_tree.yview)
        queue_scroll.grid(row=0, column=1, sticky="ns")
        self.queue_tree.configure(yscrollcommand=queue_scroll.set)

        hint_text = (
            "Drag files or folders here." if DND_AVAILABLE
            else "Drag-and-drop is optional. Install tkinterdnd2 to enable it."
        )
        self.drop_hint = ttk.Label(queue_panel, text=hint_text, style="Muted.TLabel")
        self.drop_hint.grid(row=2, column=0, sticky="w", pady=(5, 0))

        # Transcript pane
        transcript_panel = ttk.Frame(workspace, padding=(8, 0, 0, 0))
        workspace.add(transcript_panel, weight=5)
        transcript_panel.columnconfigure(0, weight=1)
        transcript_panel.rowconfigure(1, weight=1)

        transcript_toolbar = ttk.Frame(transcript_panel)
        transcript_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        transcript_toolbar.columnconfigure(1, weight=1)
        ttk.Label(transcript_toolbar, text="Transcript", font=("Segoe UI Semibold", 12)).grid(row=0, column=0, sticky="w", padx=(0, 12))

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(transcript_toolbar, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew")
        self.search_entry.bind("<Return>", lambda e: self.find_next())
        ttk.Button(transcript_toolbar, text="Find", command=self.find_next).grid(row=0, column=2, padx=(6, 0))

        editor_box = ttk.Frame(transcript_panel)
        editor_box.grid(row=1, column=0, sticky="nsew")
        editor_box.columnconfigure(0, weight=1)
        editor_box.rowconfigure(0, weight=1)

        self.transcript_text = tk.Text(
            editor_box,
            wrap="word",
            undo=True,
            font=("Segoe UI", 10),
            relief="solid",
            borderwidth=1,
            padx=12,
            pady=10
        )
        self.transcript_text.grid(row=0, column=0, sticky="nsew")
        editor_scroll = ttk.Scrollbar(editor_box, orient="vertical", command=self.transcript_text.yview)
        editor_scroll.grid(row=0, column=1, sticky="ns")
        self.transcript_text.configure(yscrollcommand=editor_scroll.set)
        self.transcript_text.tag_configure("search_hit", background="#fff3a3")

        editor_actions = ttk.Frame(transcript_panel)
        editor_actions.grid(row=2, column=0, sticky="ew", pady=(7, 0))
        ttk.Button(editor_actions, text="Copy", command=self.copy_transcript).pack(side="left", padx=(0, 5))
        ttk.Button(editor_actions, text="Save Edited Copy", command=self.save_edited_copy).pack(side="left", padx=5)
        ttk.Button(editor_actions, text="Clear Preview", command=lambda: self.transcript_text.delete("1.0", tk.END)).pack(side="left", padx=5)

        # Bottom action and progress area
        footer = ttk.Frame(outer)
        footer.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        footer.columnconfigure(2, weight=1)

        self.start_button = ttk.Button(
            footer,
            text="Start Transcription",
            command=self.start_batch,
            state="disabled",
            style="Primary.TButton"
        )
        self.start_button.grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.cancel_button = ttk.Button(
            footer,
            text="Cancel",
            command=self.cancel_batch,
            state="disabled",
            style="Danger.TButton"
        )
        self.cancel_button.grid(row=0, column=1, sticky="w", padx=(0, 12))

        progress_wrap = ttk.Frame(footer)
        progress_wrap.grid(row=0, column=2, sticky="ew")
        progress_wrap.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(progress_wrap, mode="determinate", maximum=100)
        self.progress.grid(row=0, column=0, sticky="ew")
        self.progress_label = ttk.Label(progress_wrap, text="0%", width=7, anchor="e")
        self.progress_label.grid(row=0, column=1, padx=(8, 0))

        self.status_label = ttk.Label(outer, text="Ready.", style="Muted.TLabel")
        self.status_label.grid(row=4, column=0, sticky="ew", pady=(7, 0))

    def apply_settings_to_ui(self):
        self.model_var.set(self.settings.get("model", "small"))
        self.language_var.set(self.settings.get("language", "English"))
        self.hardware_var.set(self.settings.get("hardware", "Auto"))
        saved_type = self.settings.get("content_type", self.settings.get("profile", "Lecture / Course"))
        if saved_type not in CONTENT_TYPES:
            saved_type = "Lecture / Course"
        self.content_type_var.set(saved_type)
        self.output_folder_var.set(self.settings.get("output_folder", ""))
        self.export_txt_var.set(self.settings.get("export_txt", True))
        self.export_timestamped_var.set(self.settings.get("export_timestamped", True))
        self.export_srt_var.set(self.settings.get("export_srt", True))
        self.context_notes.delete("1.0", tk.END)
        self.context_notes.insert("1.0", self.settings.get("context_notes", ""))

    # --------------------------------------------------------
    # Dependency setup / hardware
    # --------------------------------------------------------
    def start_dependency_check(self):
        threading.Thread(target=self.setup_engine, daemon=True).start()

    def setup_engine(self):
        try:
            self.set_status("Checking faster-whisper...")
            try:
                faster_whisper = importlib.import_module("faster_whisper")
            except ImportError:
                self.set_status("First launch: installing faster-whisper. This can take a minute...")
                result = subprocess.run(
                    [python_for_pip(), "-m", "pip", "install", "--upgrade", "faster-whisper"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=hidden_process_flags(),
                )
                if result.returncode != 0:
                    raise RuntimeError("Could not install faster-whisper:\n\n" + result.stderr[-2500:])
                importlib.invalidate_caches()
                faster_whisper = importlib.import_module("faster_whisper")

            self.WhisperModel = faster_whisper.WhisperModel
            self.ctranslate2 = importlib.import_module("ctranslate2")

            cuda_count = 0
            try:
                cuda_count = int(self.ctranslate2.get_cuda_device_count())
            except Exception:
                cuda_count = 0

            self.root.after(0, self.engine_ready, cuda_count)
        except Exception as exc:
            write_error_log("Engine setup", exc)
            self.root.after(0, self.engine_failed, str(exc))

    def engine_ready(self, cuda_count):
        if cuda_count > 0:
            runtime = "CUDA 12 runtime found" if self.cuda_runtime_dirs else "CUDA device detected"
            text = f"Engine ready | {self.gpu_name} | {runtime}"
        else:
            text = "Engine ready | CPU mode available"
        self.engine_status.config(text=text)
        for widget in [self.add_files_button, self.add_folder_button, self.remove_button, self.clear_button, self.start_button]:
            widget.config(state="normal")
        self.hardware_test_button.config(state="normal")
        self.status_label.config(text="Ready. Add media files to the queue, or run Test Hardware.")

    def engine_failed(self, error):
        self.engine_status.config(text="Engine setup failed")
        messagebox.showerror("Setup Error", error)

    # --------------------------------------------------------
    # Real hardware verification
    # --------------------------------------------------------
    def start_hardware_test(self):
        if self.hardware_test_running:
            return
        if not self.WhisperModel or not self.ctranslate2:
            messagebox.showinfo("Hardware Test", "The transcription engine is still starting.")
            return
        self.hardware_test_running = True
        self.hardware_test_button.config(state="disabled")
        self.set_status("Testing actual CUDA inference...")
        threading.Thread(target=self.run_hardware_test, daemon=True).start()

    def run_hardware_test(self):
        try:
            cuda_count = int(self.ctranslate2.get_cuda_device_count())
            if cuda_count < 1:
                raise RuntimeError("CTranslate2 does not detect an NVIDIA CUDA device.")

            model_name = self.model_var.get() or "small"
            model = self.WhisperModel(model_name, device="cuda", compute_type="float16")
            self.verify_cuda_inference(model)
            key = (model_name, "cuda", "float16")
            self.cuda_verified_keys.add(key)
            self.loaded_model = model
            self.loaded_model_key = key
            self.root.after(0, self.hardware_test_success, model_name)
        except Exception as exc:
            write_error_log("Hardware self-test", exc)
            self.root.after(0, self.hardware_test_failed, f"{type(exc).__name__}: {exc}")

    def verify_cuda_inference(self, model):
        """Force a tiny real inference pass so missing runtime DLLs fail here, not mid-file."""
        try:
            import numpy as np
        except ImportError:
            result = subprocess.run(
                [python_for_pip(), "-m", "pip", "install", "numpy"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=hidden_process_flags(),
            )
            if result.returncode != 0:
                raise RuntimeError("NumPy is required for the CUDA self-test.")
            importlib.invalidate_caches()
            import numpy as np

        # One second of silence. Iterating the generator forces CTranslate2 to execute on the GPU.
        audio = np.zeros(16000, dtype=np.float32)
        segments, _ = model.transcribe(
            audio,
            language="en",
            beam_size=1,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        list(segments)

    def hardware_test_success(self, model_name):
        self.hardware_test_running = False
        self.hardware_test_button.config(state="normal")
        self.engine_status.config(text=f"GPU verified | {self.gpu_name} | CUDA FP16")
        self.status_label.config(text=f"Hardware test passed using {model_name} on {self.gpu_name} (CUDA FP16).")
        messagebox.showinfo(
            "Hardware Test",
            f"GPU transcription is working.\n\n{self.gpu_name}\nCUDA FP16\nModel tested: {model_name}"
        )

    def hardware_test_failed(self, error):
        self.hardware_test_running = False
        self.hardware_test_button.config(state="normal")
        self.engine_status.config(text=f"GPU test failed | CPU fallback available")
        self.status_label.config(text="GPU self-test failed. Auto mode will fall back to CPU.")
        messagebox.showerror(
            "Hardware Test Failed",
            "The NVIDIA GPU was detected, but real Whisper inference failed.\n\n"
            + error
            + "\n\nAuto mode can still use the CPU."
        )

    # --------------------------------------------------------
    # Drag/drop and queue
    # --------------------------------------------------------
    def setup_drag_drop(self):
        if not DND_AVAILABLE:
            return
        try:
            self.queue_tree.drop_target_register(DND_FILES)
            self.queue_tree.dnd_bind("<<Drop>>", self.handle_drop)
        except Exception as exc:
            write_error_log("Drag/drop setup", exc)

    def handle_drop(self, event):
        try:
            paths = self.root.tk.splitlist(event.data)
            for raw in paths:
                path = os.path.abspath(raw)
                if os.path.isdir(path):
                    self.add_folder_path(path)
                elif self.is_supported_file(path):
                    self.enqueue_file(path)
            self.update_queue_controls()
        except Exception as exc:
            write_error_log("Handling drag/drop", exc)

    def is_supported_file(self, path):
        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    def add_files(self):
        initial = self.settings.get("last_input_folder") or os.getcwd()
        paths = filedialog.askopenfilenames(
            title="Add audio or video files",
            initialdir=initial,
            filetypes=[
                ("Media files", "*.mp4 *.mp3 *.wav *.m4a *.mov *.mkv *.webm *.aac *.flac *.ogg *.wma *.mpeg *.mpg"),
                ("All files", "*.*"),
            ],
        )
        for path in paths:
            if self.is_supported_file(path):
                self.enqueue_file(os.path.abspath(path))
        if paths:
            self.settings["last_input_folder"] = os.path.dirname(paths[0])
        self.update_queue_controls()

    def add_folder(self):
        initial = self.settings.get("last_input_folder") or os.getcwd()
        folder = filedialog.askdirectory(title="Add media folder", initialdir=initial)
        if folder:
            self.settings["last_input_folder"] = folder
            self.add_folder_path(folder)
            self.update_queue_controls()

    def add_folder_path(self, folder):
        found = []
        for root, _, files in os.walk(folder):
            for name in files:
                path = os.path.join(root, name)
                if self.is_supported_file(path):
                    found.append(path)
        for path in sorted(found):
            self.enqueue_file(os.path.abspath(path))

    def enqueue_file(self, path):
        if any(job["path"] == path for job in self.queue):
            return
        job = {
            "path": path,
            "status": "Waiting",
            "outputs": [],
            "error": "",
        }
        iid = self.queue_tree.insert("", "end", values=(os.path.basename(path), "Waiting", ""))
        job["iid"] = iid
        self.queue_tree_to_job[iid] = job
        self.queue.append(job)

    def remove_selected(self):
        if self.processing:
            return
        selected = set(self.queue_tree.selection())
        if not selected:
            return
        new_queue = []
        for job in self.queue:
            if job["iid"] in selected:
                self.queue_tree.delete(job["iid"])
                self.queue_tree_to_job.pop(job["iid"], None)
            else:
                new_queue.append(job)
        self.queue = new_queue
        self.update_queue_controls()

    def clear_queue(self):
        if self.processing:
            return
        for iid in self.queue_tree.get_children():
            self.queue_tree.delete(iid)
        self.queue.clear()
        self.queue_tree_to_job.clear()
        self.update_queue_controls()

    def update_queue_controls(self):
        if self.processing:
            return
        state = "normal" if self.queue else "disabled"
        self.start_button.config(state=state)

    # --------------------------------------------------------
    # Output controls
    # --------------------------------------------------------
    def choose_output_folder(self):
        folder = filedialog.askdirectory(title="Choose transcript output folder")
        if folder:
            self.output_folder_var.set(folder)

    def open_output_folder(self):
        folder = self.output_folder_var.get().strip()
        if not folder and self.queue:
            folder = os.path.dirname(self.queue[0]["path"])
        if not folder or not os.path.isdir(folder):
            messagebox.showinfo("Output Folder", "Choose an output folder or add a source file first.")
            return
        try:
            if os.name == "nt":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as exc:
            write_error_log("Opening output folder", exc)

    def make_unique_output_stem(self, folder, source_path):
        base = Path(source_path).stem
        stem = f"{base}_transcript"
        candidate = stem
        n = 2
        while any(Path(folder, candidate + ext).exists() for ext in [".txt", "_timestamped.txt", ".srt", "_edited.txt"]):
            candidate = f"{stem}_{n}"
            n += 1
        return candidate

    # --------------------------------------------------------
    # Batch processing
    # --------------------------------------------------------
    def start_batch(self):
        if self.processing or not self.queue:
            return
        if not any([self.export_txt_var.get(), self.export_timestamped_var.get(), self.export_srt_var.get()]):
            messagebox.showerror("No Output Selected", "Select at least one output format.")
            return

        self.save_settings()
        self.run_options = {
            "model": self.model_var.get(),
            "language": self.language_var.get(),
            "hardware": self.hardware_var.get(),
            "content_type": self.content_type_var.get(),
            "context_notes": self.context_notes.get("1.0", tk.END).strip(),
            "output_folder": self.output_folder_var.get().strip(),
            "export_txt": bool(self.export_txt_var.get()),
            "export_timestamped": bool(self.export_timestamped_var.get()),
            "export_srt": bool(self.export_srt_var.get()),
        }
        self.cancel_event.clear()
        self.processing = True
        self.queue_index = 0
        self.progress["value"] = 0
        self.progress_label.config(text="0%")
        self.transcript_text.delete("1.0", tk.END)

        self.start_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        for widget in [self.add_files_button, self.add_folder_button, self.remove_button, self.clear_button, self.hardware_test_button]:
            widget.config(state="disabled")

        for job in self.queue:
            if job["status"] in {"Finished", "Failed", "Cancelled"}:
                job["status"] = "Waiting"
                self.update_job_status(job, "Waiting", "")

        threading.Thread(target=self.process_batch, daemon=True).start()

    def cancel_batch(self):
        if not self.processing:
            return
        self.cancel_event.set()
        self.cancel_button.config(state="disabled")
        self.status_label.config(text="Cancellation requested. Waiting for the current decoding segment to finish...")

    def process_batch(self):
        try:
            total = len(self.queue)
            for index, job in enumerate(self.queue, start=1):
                if self.cancel_event.is_set():
                    break
                self.queue_index = index
                self.process_one(job, index, total)

            if self.cancel_event.is_set():
                self.root.after(0, self.batch_cancelled)
            else:
                self.root.after(0, self.batch_finished)
        except Exception as exc:
            write_error_log("Batch processing", exc)
            self.root.after(0, self.batch_crashed, str(exc))

    def resolve_device(self):
        requested = self.run_options["hardware"]
        cuda_count = 0
        try:
            cuda_count = int(self.ctranslate2.get_cuda_device_count()) if self.ctranslate2 else 0
        except Exception:
            cuda_count = 0

        if requested == "CPU":
            return "cpu", "int8"
        if requested == "NVIDIA GPU":
            if cuda_count < 1:
                raise RuntimeError("NVIDIA GPU was selected, but CTranslate2 did not detect a CUDA device.")
            return "cuda", "float16"
        if cuda_count > 0:
            return "cuda", "float16"
        return "cpu", "int8"

    def get_or_load_model(self):
        model_name = self.run_options["model"]
        device, compute_type = self.resolve_device()
        key = (model_name, device, compute_type)

        if self.loaded_model is not None and self.loaded_model_key == key:
            return self.loaded_model, device, compute_type

        self.set_status(f"Loading {model_name} on {device.upper()}...")
        try:
            model = self.WhisperModel(model_name, device=device, compute_type=compute_type)

            # A CUDA device can be detected even when a required runtime DLL is unavailable.
            # Force a tiny inference pass before touching the user's media file.
            if device == "cuda" and key not in self.cuda_verified_keys:
                self.set_status(f"Verifying {self.gpu_name} with real CUDA inference...")
                self.verify_cuda_inference(model)
                self.cuda_verified_keys.add(key)
                self.root.after(
                    0,
                    lambda: self.engine_status.config(
                        text=f"GPU verified | {self.gpu_name} | CUDA FP16"
                    )
                )

        except Exception as exc:
            if device == "cuda" and self.run_options["hardware"] == "Auto":
                write_error_log("CUDA verification failed; using CPU", exc)
                self.set_status("GPU verification failed. Falling back to CPU...")
                model = self.WhisperModel(model_name, device="cpu", compute_type="int8")
                device, compute_type = "cpu", "int8"
                key = (model_name, device, compute_type)
            else:
                raise

        self.loaded_model = model
        self.loaded_model_key = key
        return model, device, compute_type

    def build_initial_prompt(self):
        content_type = self.run_options.get("content_type", "General / Other")
        base_prompt = CONTENT_TYPES.get(content_type, CONTENT_TYPES["General / Other"])
        context = self.run_options.get("context_notes", "").strip()
        if context:
            return f"{base_prompt} Additional context and terms to preserve: {context}"
        return base_prompt

    def collect_transcription(self, model, path, language, prompt, index, total, device, compute_type):
        segments, info = model.transcribe(
            path,
            language=language,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=True,
            initial_prompt=prompt or None,
        )

        duration = float(getattr(info, "duration", 0) or 0)
        start_time = time.time()
        plain_lines = []
        timestamp_lines = []
        srt_lines = []
        srt_index = 1

        for segment in segments:
            if self.cancel_event.is_set():
                return None

            text = segment.text.strip()
            if not text:
                continue

            plain_lines.append(text + "\n")
            timestamp_lines.append(f"[{format_clock(segment.start)}] {text}\n")
            srt_lines.append(
                f"{srt_index}\n"
                f"{format_srt_time(segment.start)} --> {format_srt_time(segment.end)}\n"
                f"{text}\n\n"
            )
            srt_index += 1

            self.root.after(0, self.append_transcript, f"[{format_clock(segment.start)}] {text}\n\n")

            if duration > 0:
                fraction = min(1.0, float(segment.end) / duration)
                elapsed = time.time() - start_time
                eta = (elapsed / fraction - elapsed) if fraction > 0.01 else 0
                self.root.after(
                    0,
                    self.update_progress,
                    fraction * 100,
                    index,
                    total,
                    elapsed,
                    eta,
                    os.path.basename(path),
                )

        return {
            "plain": "".join(plain_lines),
            "timestamped": "".join(timestamp_lines),
            "srt": "".join(srt_lines),
            "elapsed": time.time() - start_time,
            "language": getattr(info, "language", None),
        }

    def write_outputs(self, folder, stem, result):
        os.makedirs(folder, exist_ok=True)
        planned = []
        if self.run_options["export_txt"]:
            planned.append((os.path.join(folder, stem + ".txt"), result["plain"]))
        if self.run_options["export_timestamped"]:
            planned.append((os.path.join(folder, stem + "_timestamped.txt"), result["timestamped"]))
        if self.run_options["export_srt"]:
            planned.append((os.path.join(folder, stem + ".srt"), result["srt"]))

        created = []
        try:
            for path, content in planned:
                with open(path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(content)
                created.append(path)
            return created
        except Exception:
            # Do not leave incomplete output files behind if saving fails.
            for path in created:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass
            raise

    def process_one(self, job, index, total):
        path = job["path"]
        job["error"] = ""
        self.update_job_status(job, "Loading", "")
        self.root.after(0, lambda: self.transcript_text.delete("1.0", tk.END))

        try:
            model, device, compute_type = self.get_or_load_model()
            if self.cancel_event.is_set():
                self.update_job_status(job, "Cancelled", "")
                return

            language = "en" if self.run_options["language"] == "English" else None
            prompt = self.build_initial_prompt()

            if device == "cuda":
                hw_detail = f"{self.gpu_name} | CUDA {compute_type}"
            else:
                hw_detail = f"CPU | {compute_type}"
            self.update_job_status(job, "Transcribing", hw_detail)
            self.set_status(
                f"File {index}/{total}: {os.path.basename(path)} | {hw_detail}"
            )

            try:
                result = self.collect_transcription(
                    model, path, language, prompt, index, total, device, compute_type
                )
            except Exception as gpu_exc:
                # CTranslate2 can detect a GPU even when the required CUDA runtime DLLs
                # are unavailable. In Auto mode, retry the whole file on CPU.
                if device == "cuda" and self.run_options["hardware"] == "Auto" and not self.cancel_event.is_set():
                    write_error_log(f"GPU attempt failed for {path}; retrying on CPU", gpu_exc)
                    self.set_status("GPU transcription failed. Retrying this file on CPU...")
                    self.update_job_status(job, "Retrying", "GPU failed; using CPU")
                    self.root.after(0, lambda: self.transcript_text.delete("1.0", tk.END))
                    self.loaded_model = None
                    self.loaded_model_key = None
                    model = self.WhisperModel(self.run_options["model"], device="cpu", compute_type="int8")
                    self.loaded_model = model
                    self.loaded_model_key = (self.run_options["model"], "cpu", "int8")
                    device, compute_type = "cpu", "int8"
                    result = self.collect_transcription(
                        model, path, language, prompt, index, total, device, compute_type
                    )
                else:
                    raise

            if result is None or self.cancel_event.is_set():
                self.update_job_status(job, "Cancelled", "")
                return

            folder = self.run_options["output_folder"] or os.path.dirname(path)
            stem = self.make_unique_output_stem(folder, path)
            outputs = self.write_outputs(folder, stem, result)

            job["outputs"] = outputs
            self.current_output_folder = folder
            detected = result.get("language")
            detail = f"{self.gpu_name} | CUDA {compute_type}" if device == "cuda" else f"CPU | {compute_type}"
            if detected:
                detail += f" | {detected}"
            self.update_job_status(job, "Finished", detail)
            self.root.after(
                0,
                self.update_progress,
                100.0,
                index,
                total,
                result.get("elapsed", 0),
                0,
                os.path.basename(path),
            )

        except Exception as exc:
            write_error_log(f"Transcribing {path}", exc)
            job["error"] = f"{type(exc).__name__}: {exc}"
            short_error = job["error"].replace("\n", " ")[:180]
            self.update_job_status(job, "Failed", short_error)
            self.set_status(f"Failed: {os.path.basename(path)} | {short_error}")

    # --------------------------------------------------------
    # UI updates from worker thread
    # --------------------------------------------------------
    def update_job_status(self, job, status, details=None):
        job["status"] = status
        if details is not None:
            self.root.after(0, lambda: self.queue_tree.set(job["iid"], "details", details))
        self.root.after(0, lambda: self.queue_tree.set(job["iid"], "status", status))

    def set_status(self, text):
        self.root.after(0, lambda: self.status_label.config(text=text))

    def append_transcript(self, text):
        self.transcript_text.insert(tk.END, text)
        self.transcript_text.see(tk.END)

    def update_progress(self, percent, index, total, elapsed, eta, name):
        self.progress["value"] = percent
        self.progress_label.config(text=f"{percent:5.1f}%")
        self.status_label.config(
            text=(
                f"File {index}/{total}: {name} | "
                f"Elapsed {format_clock(elapsed)} | ETA {format_clock(eta)}"
            )
        )

    def batch_finished(self):
        self.processing = False
        self.cancel_button.config(state="disabled")
        for widget in [self.add_files_button, self.add_folder_button, self.remove_button, self.clear_button, self.hardware_test_button]:
            widget.config(state="normal")
        self.start_button.config(state="normal" if self.queue else "disabled")

        finished = sum(1 for job in self.queue if job["status"] == "Finished")
        failed = sum(1 for job in self.queue if job["status"] == "Failed")
        cancelled = sum(1 for job in self.queue if job["status"] == "Cancelled")

        if failed == 0 and cancelled == 0:
            self.progress["value"] = 100
            self.progress_label.config(text="100%")
            self.status_label.config(text=f"Batch complete. {finished} file(s) finished.")
            messagebox.showinfo("Finished", f"Completed {finished} file(s) successfully.")
        else:
            self.status_label.config(
                text=f"Batch complete: {finished} finished, {failed} failed, {cancelled} cancelled."
            )
            messagebox.showwarning(
                "Batch Complete",
                f"Finished: {finished}\nFailed: {failed}\nCancelled: {cancelled}\n\n"
                "For failed files, the Details column shows the error. Full errors are also saved to the app error log."
            )

    def batch_cancelled(self):
        self.processing = False
        self.cancel_button.config(state="disabled")
        for widget in [self.add_files_button, self.add_folder_button, self.remove_button, self.clear_button, self.hardware_test_button]:
            widget.config(state="normal")
        self.start_button.config(state="normal" if self.queue else "disabled")
        self.status_label.config(text="Batch cancelled.")

    def batch_crashed(self, error):
        self.processing = False
        self.cancel_button.config(state="disabled")
        for widget in [self.add_files_button, self.add_folder_button, self.remove_button, self.clear_button, self.hardware_test_button]:
            widget.config(state="normal")
        self.start_button.config(state="normal" if self.queue else "disabled")
        messagebox.showerror("Batch Error", error)

    # --------------------------------------------------------
    # Transcript editor / search
    # --------------------------------------------------------
    def copy_transcript(self):
        text = self.transcript_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Copy Transcript", "There is no transcript to copy.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_label.config(text="Transcript copied to clipboard.")

    def save_edited_copy(self):
        text = self.transcript_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Save Edited Copy", "There is no transcript to save.")
            return

        folder = self.output_folder_var.get().strip() or self.current_output_folder
        if not folder and self.queue:
            folder = os.path.dirname(self.queue[0]["path"])
        if not folder:
            folder = os.getcwd()

        default_name = "edited_transcript.txt"
        if self.queue:
            default_name = Path(self.queue[min(max(self.queue_index - 1, 0), len(self.queue) - 1)]["path"]).stem + "_edited.txt"

        path = filedialog.asksaveasfilename(
            title="Save edited transcript",
            initialdir=folder,
            initialfile=default_name,
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")],
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text + "\n")
            self.status_label.config(text=f"Saved edited copy: {os.path.basename(path)}")

    def find_next(self):
        query = self.search_var.get().strip()
        self.transcript_text.tag_remove("search_hit", "1.0", tk.END)
        if not query:
            return

        start = self.transcript_text.index(tk.INSERT)
        pos = self.transcript_text.search(query, start, stopindex=tk.END, nocase=True)
        if not pos:
            pos = self.transcript_text.search(query, "1.0", stopindex=start, nocase=True)
        if not pos:
            self.status_label.config(text=f'No match for "{query}".')
            return

        end = f"{pos}+{len(query)}c"
        self.transcript_text.tag_add("search_hit", pos, end)
        self.transcript_text.mark_set(tk.INSERT, end)
        self.transcript_text.see(pos)
        self.transcript_text.focus_set()

    # --------------------------------------------------------
    # Shutdown
    # --------------------------------------------------------
    def on_close(self):
        self.save_settings()
        if self.processing:
            if not messagebox.askyesno("Exit", "A transcription is still running. Cancel it and exit?"):
                return
            self.cancel_event.set()
        self.root.destroy()


def make_root():
    if DND_AVAILABLE:
        return TkinterDnD.Tk()
    return tk.Tk()


def main():
    root = make_root()
    app = TranscriptionApp(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        write_error_log("Fatal application error", exc)
        try:
            error_root = tk.Tk()
            error_root.withdraw()
            messagebox.showerror(
                "Local AI Transcriber",
                f"The application encountered a fatal error:\n\n{type(exc).__name__}: {exc}\n\n"
                f"Details were written to:\n{ERROR_LOG}"
            )
            error_root.destroy()
        except Exception:
            pass
