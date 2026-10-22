
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from transcriber import transcribe_to_srt


class WhereMySubsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("where-my-subs")
        self.root.geometry("680x440")
        self.root.minsize(580, 400)

        self.events = queue.Queue()
        self.worker = None

        self.audio_path = tk.StringVar()
        # self.model_name = tk.StringVar(value="small")
        self.model_name = tk.StringVar(value="medium")
        self.device = tk.StringVar(value="cpu")
        self.compute_type = tk.StringVar(value="int8")
        self.status = tk.StringVar(
            value="Choose an audio file to get started."
        )
        self.progress_text = tk.StringVar(value="")

        self.build_ui()
        self.root.after(100, self.process_events)

    def build_ui(self):
        outer = ttk.Frame(self.root, padding=22)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="where-my-subs",
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            outer,
            text="Convert audio into timestamped SRT subtitles.",
        ).pack(anchor="w", pady=(4, 18))

        file_frame = ttk.LabelFrame(
            outer, text="Audio file", padding=12
        )
        file_frame.pack(fill="x")

        ttk.Entry(
            file_frame, textvariable=self.audio_path
        ).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )

        ttk.Button(
            file_frame,
            text="Browse...",
            command=self.choose_file,
        ).pack(side="right")

        options = ttk.LabelFrame(
            outer, text="Transcription settings", padding=12
        )
        options.pack(fill="x", pady=14)

        ttk.Label(options, text="Model").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Combobox(
            options,
            textvariable=self.model_name,
            state="readonly",
            values=("tiny", "base", "small", "medium"),
            width=12,
        ).grid(row=1, column=0, sticky="w", padx=(0, 20))

        ttk.Label(options, text="Device").grid(
            row=0, column=1, sticky="w"
        )
        device_box = ttk.Combobox(
            options,
            textvariable=self.device,
            state="readonly",
            values=("cpu", "cuda"),
            width=12,
        )
        device_box.grid(
            row=1, column=1, sticky="w", padx=(0, 20)
        )
        device_box.bind(
            "<<ComboboxSelected>>", self.update_compute_types
        )

        ttk.Label(options, text="Compute type").grid(
            row=0, column=2, sticky="w"
        )
        self.compute_box = ttk.Combobox(
            options,
            textvariable=self.compute_type,
            state="readonly",
            values=("int8", "float32"),
            width=15,
        )
        self.compute_box.grid(row=1, column=2, sticky="w")

        ttk.Label(
            options,
            text=(
                "Recommended starting settings: small / CPU / int8. "
                "CUDA requires compatible NVIDIA runtime libraries."
            ),
            wraplength=590,
        ).grid(
            row=2, column=0, columnspan=3,
            sticky="w", pady=(12, 0)
        )

        self.start_button = ttk.Button(
            outer,
            text="Generate subtitles",
            command=self.start_transcription,
        )
        self.start_button.pack(anchor="w")

        self.progress = ttk.Progressbar(
            outer, mode="indeterminate"
        )
        self.progress.pack(fill="x", pady=(14, 5))

        ttk.Label(
            outer, textvariable=self.status, wraplength=620
        ).pack(anchor="w")

        ttk.Label(
            outer, textvariable=self.progress_text
        ).pack(anchor="w", pady=(4, 0))

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Select an audio file",
            filetypes=[
                ("Audio files", "*.mp3 *.wav *.m4a *.flac *.ogg"),
                ("All files", "*.*"),
            ],
        )

        if path:
            self.audio_path.set(path)

    def update_compute_types(self, _event=None):
        if self.device.get() == "cuda":
            choices = ("float16", "int8_float16", "int8")
            self.compute_box.configure(values=choices)

            if self.compute_type.get() not in choices:
                self.compute_type.set("float16")
        else:
            choices = ("int8", "float32")
            self.compute_box.configure(values=choices)
            self.compute_type.set("int8")

    def start_transcription(self):
        path = self.audio_path.get().strip()

        if not path:
            messagebox.showwarning(
                "Choose a file", "Select an audio file first."
            )
            return

        audio_path = Path(path)

        if not audio_path.is_file():
            messagebox.showerror(
                "File not found", f"Cannot find:\n{audio_path}"
            )
            return

        supported = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
        if audio_path.suffix.lower() not in supported:
            messagebox.showwarning(
                "Unsupported file",
                "Select an MP3, WAV, M4A, FLAC, or OGG file.",
            )
            return

        if self.worker and self.worker.is_alive():
            return

        options = (
            audio_path,
            self.model_name.get(),
            self.device.get(),
            self.compute_type.get(),
        )

        self.start_button.configure(state="disabled")
        self.progress.start(10)
        self.status.set(
            "Loading model and transcribing. Please wait..."
        )
        self.progress_text.set("")

        self.worker = threading.Thread(
            target=self.worker_task,
            args=options,
            daemon=True,
        )
        self.worker.start()

    def worker_task(
        self, audio_path, model_name, device, compute_type
    ):
        try:
            output_path = transcribe_to_srt(
                audio_path=audio_path,
                model_name=model_name,
                device=device,
                compute_type=compute_type,
                progress_callback=lambda count: self.events.put(
                    ("progress", count)
                ),
            )
            self.events.put(("success", str(output_path)))

        except Exception as exc:
            self.events.put(("error", str(exc)))

    def process_events(self):
        try:
            while True:
                event, value = self.events.get_nowait()

                if event == "progress":
                    self.status.set("Transcribing...")
                    self.progress_text.set(
                        f"Segments written: {value}"
                    )

                elif event == "success":
                    self.progress.stop()
                    self.start_button.configure(state="normal")
                    self.status.set("Transcription complete.")
                    self.progress_text.set("")
                    messagebox.showinfo(
                        "Subtitles created",
                        f"Saved subtitle file:\n{value}",
                    )

                elif event == "error":
                    self.progress.stop()
                    self.start_button.configure(state="normal")
                    self.status.set("Transcription failed.")
                    self.progress_text.set("")
                    messagebox.showerror(
                        "Transcription failed", value
                    )

        except queue.Empty:
            pass

        self.root.after(100, self.process_events)


if __name__ == "__main__":
    root = tk.Tk()
    app = WhereMySubsApp(root)
    root.mainloop()
