"""
Native Typing Simulator
"""

from __future__ import annotations

import random
import time
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import pyautogui

SAMPLE_TEXT = "Paste your draft here, then press Start."

screen_width, screen_height = pyautogui.size()

class TypingSimulatorApp(tk.Tk):
    """Tkinter application that animates text into a document-style preview."""

    def __init__(self) -> None:
        super().__init__()

        self.title("Typing Simulator")
        self.geometry("1180x760")
        self.minsize(860, 560)

        # Runtime typing state. `position` tracks the next source character
        self.source_text = ""
        self.position = 0
        self.running = False
        self.timer_id: str | None = None
        self.elapsed_timer_id: str | None = None
        self.started_at = 0.0
        self.typo_cleanup = False

        # Build the visual style and interface once at startup.
        self._build_style()
        self._build_ui()
        self._update_metrics()

    def _build_style(self) -> None:
        """Configure ttk colors, fonts, and button styles."""

        self.attributes("-topmost", True)
        self.configure(bg="#f4f6f8")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f6f8")
        style.configure("Panel.TFrame", background="#ffffff", relief="flat")
        style.configure("TLabel", background="#f4f6f8", foreground="#17202a", font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background="#ffffff", foreground="#17202a", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#f4f6f8", foreground="#17202a", font=("Segoe UI", 16, "bold"))
        style.configure("Metric.TLabel", background="#ffffff", foreground="#17202a", font=("Segoe UI", 18, "bold"))
        style.configure("Muted.TLabel", background="#ffffff", foreground="#5d6b7a", font=("Segoe UI", 9))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 8))
        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 8))
        style.configure("Reset.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 8))
        style.map("Accent.TButton", background=[("active", "#157a42"), ("!disabled", "#16834a")], foreground=[("!disabled", "#ffffff")])
        style.map("Danger.TButton", background=[("active", "#a93530"), ("!disabled", "#c2413b")], foreground=[("!disabled", "#ffffff")])

    def _build_ui(self) -> None:
        """Create the header, controls panel, metrics panel, and preview area."""

        # Top bar with the app name and current typing status.
        header = ttk.Frame(self, padding=(18, 14, 18, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        mark = tk.Label(
            header,
            text="T",
            bg="#2563eb",
            fg="white",
            font=("Segoe UI", 13, "bold"),
            width=2,
            height=1,
        )
        mark.grid(row=0, column=0, padx=(0, 10))
        ttk.Label(header, text="Typing Simulator", style="Title.TLabel").grid(row=0, column=1, sticky="w")
        self.status_label = ttk.Label(header, text="Ready", foreground="#5d6b7a")
        self.status_label.grid(row=0, column=2, sticky="e")

        body = ttk.Frame(self, padding=(18, 8, 18, 18))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, minsize=330)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # Left side: input text, timing controls, and action buttons.
        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        left.rowconfigure(1, weight=1)

        controls = ttk.Frame(left, style="Panel.TFrame", padding=14)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(0, weight=1)

        ttk.Label(controls, text="Text", style="Panel.TLabel", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.input_box = ScrolledText(
            controls,
            height=12,
            wrap="word",
            font=("Consolas", 10),
            relief="solid",
            borderwidth=1,
            undo=True,
        )
        self.input_box.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 12))
        self.input_box.insert("1.0", SAMPLE_TEXT)

        ttk.Label(controls, text="WPM", style="Panel.TLabel", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w")
        self.wpm_var = tk.IntVar(value=60)
        self.wpm_scale = ttk.Scale(
            controls,
            from_=10,
            to=180,
            orient="horizontal",
            variable=self.wpm_var,
            command=self._on_scale_change,
        )
        self.wpm_scale.grid(row=3, column=0, sticky="ew", pady=(4, 10), padx=(0, 10))
        self.wpm_spin = ttk.Spinbox(controls, from_=10, to=180, width=7, textvariable=self.wpm_var, command=self._sync_wpm)
        self.wpm_spin.grid(row=3, column=1, sticky="e", pady=(4, 10))
        controls.columnconfigure(0, weight=1)

        ttk.Label(controls, text="Rhythm", style="Panel.TLabel", font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky="w")
        self.rhythm_var = tk.StringVar(value="Natural")
        self.rhythm_box = ttk.Combobox(
            controls,
            state="readonly",
            values=("Steady", "Natural", "Bursty"),
            textvariable=self.rhythm_var,
        )
        self.rhythm_box.grid(row=5, column=0, sticky="ew", pady=(4, 10), padx=(0, 10))

        ttk.Label(controls, text="Pause %", style="Panel.TLabel", font=("Segoe UI", 10, "bold")).grid(row=4, column=1, sticky="w")
        self.pause_var = tk.IntVar(value=6)
        self.pause_spin = ttk.Spinbox(controls, from_=0, to=25, width=7, textvariable=self.pause_var)
        self.pause_spin.grid(row=5, column=1, sticky="e", pady=(4, 10))

        self.punctuation_var = tk.BooleanVar(value=True)
        self.typos_var = tk.BooleanVar(value=False)
        punctuation = ttk.Checkbutton(controls, text="Punctuation pauses", variable=self.punctuation_var)
        typos = ttk.Checkbutton(controls, text="Typos + backspace", variable=self.typos_var)
        punctuation.grid(row=6, column=0, sticky="w", pady=(0, 12))
        typos.grid(row=6, column=1, sticky="w", pady=(0, 12))

        actions = ttk.Frame(controls, style="Panel.TFrame")
        actions.grid(row=7, column=0, columnspan=2, sticky="ew")
        actions.columnconfigure((0, 1, 2), weight=1)
        self.start_button = ttk.Button(actions, text="Start", style="Accent.TButton", command=self.start_typing)
        self.stop_button = ttk.Button(actions, text="Stop", style="Danger.TButton", command=self.stop_typing, state="disabled")
        self.reset_button = ttk.Button(actions, text="Reset", style="Reset.TButton", command=self.reset_output)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.reset_button.grid(row=0, column=2, sticky="ew")

        # Live counters for the current simulation run.
        metrics = ttk.Frame(left, style="Panel.TFrame", padding=14)
        metrics.grid(row=1, column=0, sticky="new", pady=(14, 0))
        metrics.columnconfigure((0, 1, 2), weight=1)
        self.typed_value = ttk.Label(metrics, text="0", style="Metric.TLabel")
        self.left_value = ttk.Label(metrics, text="0", style="Metric.TLabel")
        self.elapsed_value = ttk.Label(metrics, text="0s", style="Metric.TLabel")
        self.typed_value.grid(row=0, column=0, sticky="w")
        self.left_value.grid(row=0, column=1, sticky="w")
        self.elapsed_value.grid(row=0, column=2, sticky="w")
        ttk.Label(metrics, text="typed", style="Muted.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Label(metrics, text="left", style="Muted.TLabel").grid(row=1, column=1, sticky="w")
        ttk.Label(metrics, text="elapsed", style="Muted.TLabel").grid(row=1, column=2, sticky="w")

        # Right side: a simple toolbar for the document-editor look, followed
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        toolbar = ttk.Frame(right, style="Panel.TFrame", padding=(10, 8))
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        for index, label in enumerate(("A", "B", "I", "=", "-", "+")):
            ttk.Label(toolbar, text=label, style="Panel.TLabel", font=("Segoe UI", 10, "bold")).grid(row=0, column=index, padx=10)

        # preview_frame = tk.Frame(right, bg="#e9edf2", highlightthickness=1, highlightbackground="#d9e0e7")
        # preview_frame.grid(row=1, column=0, sticky="nsew")
        # preview_frame.columnconfigure(0, weight=1)
        # preview_frame.rowconfigure(0, weight=1)
        #
        # self.preview = ScrolledText(
        #     preview_frame,
        #     wrap="word",
        #     font=("Arial", 12),
        #     bg="#ffffff",
        #     fg="#1f2937",
        #     relief="flat",
        #     borderwidth=0,
        #     padx=72,
        #     pady=58,
        #     undo=False,
        # )
        # self.preview.grid(row=0, column=0, sticky="nsew", padx=36, pady=22)
        # self.preview.configure(state="disabled")

    def _on_scale_change(self, _value: str) -> None:
        """Keep the WPM slider value inside the supported range."""

        self.wpm_var.set(self._clamp_int(self.wpm_var.get(), 10, 180, 60))

    def _sync_wpm(self) -> None:
        """Keep the WPM spinbox value inside the supported range."""

        self.wpm_var.set(self._clamp_int(self.wpm_var.get(), 10, 180, 60))

    @staticmethod
    def _clamp_int(value: object, minimum: int, maximum: int, fallback: int) -> int:
        """Convert a value to int and constrain it to a known safe range."""

        try:
            parsed = int(float(value))
        except (TypeError, ValueError, tk.TclError):
            return fallback
        return min(maximum, max(minimum, parsed))

    def _set_running(self, running: bool) -> None:
        """Switch the UI between idle and active typing states."""

        self.running = running
        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")
        if running:
            self.status_label.configure(text="Typing")
        elif self.source_text and self.position >= len(self.source_text):
            self.status_label.configure(text="Finished")
        else:
            self.status_label.configure(text="Ready")

    # def _set_preview_state(self, state: str) -> None:
    #     """Temporarily unlock or lock the preview text widget."""
    #
    #     self.preview.configure(state=state)

    def _append_preview(self, char: str) -> None:
        """Append one character to the preview and keep the cursor in view."""

        self._set_preview_state("normal")
        self.preview.insert("end", char)
        self.preview.see("end")
        self._set_preview_state("disabled")

    # def _delete_last_preview_char(self) -> None:
    #     """Remove the most recently displayed character for typo correction."""
    #
    #     self._set_preview_state("normal")
    #     if self.preview.index("end-1c") != "1.0":
    #         self.preview.delete("end-2c", "end-1c")
    #     self.preview.see("end")
    #     self._set_preview_state("disabled")

    def _delay_for(self, char: str, previous_char: str) -> int:
        """Calculate the next delay in milliseconds from WPM and context."""

        wpm = self._clamp_int(self.wpm_var.get(), 10, 180, 60)

        # Typing speed conversion: one "word" is conventionally treated as
        # five characters, so each character gets roughly 12000 / WPM ms.
        base_delay = 12000 / wpm
        rhythm = self.rhythm_var.get().lower()

        # Rhythm controls the randomness around the base delay.
        multiplier = random.uniform(0.72, 1.36)
        if rhythm == "steady":
            multiplier = random.uniform(0.9, 1.12)
        elif rhythm == "bursty":
            multiplier = random.uniform(0.48, 0.95) if random.random() < 0.78 else random.uniform(1.5, 2.8)

        delay = base_delay * multiplier

        # Characters that are usually slower to type get small extra delays.
        if char.isupper():
            delay += random.uniform(20, 90)
        if char.isdigit():
            delay += random.uniform(10, 70)
        if char in "[]{}()@#$%^&*_+=/\\|<>~`":
            delay += random.uniform(45, 150)
        if previous_char == "\n":
            delay += random.uniform(150, 420)

        # Optional punctuation pauses make the output feel less metronomic.
        if self.punctuation_var.get():
            if char in ".,;:":
                delay += random.uniform(120, 320)
            if char in "!?":
                delay += random.uniform(220, 520)
            if char == "\n":
                delay += random.uniform(260, 760)

        pause_chance = self._clamp_int(self.pause_var.get(), 0, 25, 6) / 100
        if char.isspace() and random.random() < pause_chance:
            delay += random.uniform(280, 1300)

        return max(8, int(delay))

    @staticmethod
    def _nearby_typo(char: str) -> str | None:
        """Return a nearby alphabetic character to simulate a typo."""

        if not char.isalpha():
            return None
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        lower = char.lower()
        if lower not in alphabet:
            return None
        index = alphabet.index(lower)
        offset = -1 if random.random() < 0.5 else 1
        typo = alphabet[(index + offset) % len(alphabet)]
        return typo if char.islower() else typo.upper()

    def start_typing(self) -> None:
        """Start or resume animating the source text into the preview."""

        if self.running:
            return

        # If the previous run finished, reload text from the input box and
        # start a fresh preview.
        if self.position >= len(self.source_text):
            self.source_text = self.input_box.get("1.0", "end-1c")
            self.position = 0
            self._clear_preview()

        if not self.source_text:
            self.source_text = self.input_box.get("1.0", "end-1c")

        if not self.source_text.strip():
            self.status_label.configure(text="Add text first")
            return

        if self.position == 0:
            self.started_at = time.monotonic()

        self._set_running(True)
        self._update_metrics()
        self._tick_elapsed()
        self._type_next()

    def stop_typing(self) -> None:
        """Pause the current run and cancel pending scheduled callbacks."""

        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        if self.elapsed_timer_id:
            self.after_cancel(self.elapsed_timer_id)
            self.elapsed_timer_id = None
        self._set_running(False)
        self._update_metrics()

    def reset_output(self) -> None:
        """Clear the preview and reset counters to the current input text."""

        self.stop_typing()
        self.source_text = self.input_box.get("1.0", "end-1c")
        self.position = 0
        self.started_at = 0.0
        self.typo_cleanup = False
        # self._clear_preview()
        self.elapsed_value.configure(text="0s")
        self.status_label.configure(text="Ready")
        self._update_metrics()

    # def _clear_preview(self) -> None:
    #     """Remove all displayed preview text."""
    #
    #     self._set_preview_state("normal")
    #     self.preview.delete("1.0", "end")
    #     self._set_preview_state("disabled")

    def _type_next(self) -> None:
        """Display the next character, then schedule the following tick."""

        if not self.running:
            return

        # A typo is shown first, then this branch deletes it before the real
        # character is typed on the next pass.
        if self.typo_cleanup:
            # self._delete_last_preview_char()
            self.typo_cleanup = False
            self.timer_id = self.after(random.randint(70, 170), self._type_next)
            return

        if self.position >= len(self.source_text):
            self.stop_typing()
            self.status_label.configure(text="Finished")
            return

        char = self.source_text[self.position]
        previous_char = self.source_text[self.position - 1] if self.position > 0 else ""

        # Optional typo mode inserts a wrong letter, then schedules a quick
        # correction before advancing the source-text position.
        if self.typos_var.get() and char.isalpha() and random.random() < 0.012:
            wrong_char = self._nearby_typo(char)
            if wrong_char:
                self._append_preview(wrong_char)
                self.typo_cleanup = True
                self.timer_id = self.after(random.randint(120, 280), self._type_next)
                return

        self._append_preview(char)
        self.position += 1
        self._update_metrics()
        self.timer_id = self.after(self._delay_for(char, previous_char), self._type_next)

    def _tick_elapsed(self) -> None:
        """Refresh elapsed time while the simulator is running."""

        if not self.running:
            return
        self._update_metrics()
        self.elapsed_timer_id = self.after(250, self._tick_elapsed)

    def _update_metrics(self) -> None:
        """Update typed, remaining, and elapsed counters."""

        total = len(self.source_text) if self.source_text else len(self.input_box.get("1.0", "end-1c"))
        self.typed_value.configure(text=str(self.position))
        self.left_value.configure(text=str(max(0, total - self.position)))
        if self.started_at:
            elapsed = int(time.monotonic() - self.started_at)
            self.elapsed_value.configure(text=f"{elapsed}s")


if __name__ == "__main__":
    app = TypingSimulatorApp()
    app.mainloop()
