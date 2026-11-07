"""
Verilog Waveform Simulator — desktop GUI.

    python gui.py

A friendly front-end over the existing parser / simulator / waveform engine:
pick a .v file, pick a module, type binary stimulus for each input, run the
simulation, and see the waveform drawn inline (no separate popup window).
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from parser import parse_verilog, list_modules
from simulator import simulate, _find_clocks, DEFAULT_SIMULATION_STEPS, TIME_STEP_PS
from waveform import draw_waveform, signal_plot_order

HERE = Path(__file__).resolve().parent

# ── palette ──────────────────────────────────────────────────────────────────
BG        = "#1e2229"
PANEL     = "#262b33"
ACCENT    = "#4CAF50"
ACCENT_HI = "#66BB6A"
TEXT      = "#e8eaed"
SUBTEXT   = "#9aa0a6"
ERROR     = "#F44336"
FONT      = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_MONO = ("Consolas", 9)
FONT_TITLE = ("Segoe UI", 15, "bold")


def _to_bin(value, width):
    return format(int(value) & ((1 << width) - 1), f"0{width}b")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Verilog Waveform Simulator")
        self.geometry("1280x820")
        self.minsize(1000, 650)
        self.configure(bg=BG)

        self.parsed = None
        self.vfile = HERE / "test.v"
        self.signal_entries = {}  # name -> ttk.Entry

        self._build_style()
        self._build_layout()
        self._load_file(self.vfile)

    # ── styling ──────────────────────────────────────────────────────────────
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=BG, foreground=TEXT, font=FONT)
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=FONT)
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=FONT)
        style.configure("Sub.TLabel", background=PANEL, foreground=SUBTEXT, font=FONT)
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=FONT_TITLE)
        style.configure("TButton", font=FONT_BOLD, padding=6)
        style.configure("Accent.TButton", font=FONT_BOLD, padding=8,
                         background=ACCENT, foreground="white")
        style.map("Accent.TButton", background=[("active", ACCENT_HI)])
        style.configure("TEntry", padding=4)
        style.configure("TCombobox", padding=4)

    # ── layout ───────────────────────────────────────────────────────────────
    def _build_layout(self):
        header = ttk.Frame(self, padding=(16, 12))
        header.pack(side="top", fill="x")
        ttk.Label(header, text="⚡ Verilog Waveform Simulator", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="  Ain Shams University — EDA Project", style="TLabel",
                  foreground=SUBTEXT).pack(side="left", padx=(8, 0))

        body = ttk.Frame(self, padding=(16, 0, 16, 16))
        body.pack(side="top", fill="both", expand=True)

        left = ttk.Frame(body, style="Panel.TFrame", padding=14)
        left.pack(side="left", fill="y", padx=(0, 12))
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)

        self._build_control_panel(left)
        self._build_result_panel(right)

        self.status = tk.StringVar(value="Ready.")
        statusbar = ttk.Label(self, textvariable=self.status, anchor="w",
                               background=PANEL, foreground=SUBTEXT, padding=(10, 4))
        statusbar.pack(side="bottom", fill="x")

    def _build_control_panel(self, parent):
        ttk.Label(parent, text="Design file", style="Panel.TLabel", font=FONT_BOLD).pack(anchor="w")
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", pady=(4, 10))
        self.file_var = tk.StringVar(value=str(self.vfile.name))
        ttk.Entry(row, textvariable=self.file_var, state="readonly", width=22).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse…", command=self._browse).pack(side="left", padx=(6, 0))

        ttk.Label(parent, text="Module", style="Panel.TLabel", font=FONT_BOLD).pack(anchor="w")
        self.module_var = tk.StringVar()
        self.module_combo = ttk.Combobox(parent, textvariable=self.module_var, state="readonly", width=24)
        self.module_combo.pack(fill="x", pady=(4, 10))
        self.module_combo.bind("<<ComboboxSelected>>", lambda e: self._load_file(self.vfile))

        ttk.Label(parent, text="Simulation steps", style="Panel.TLabel", font=FONT_BOLD).pack(anchor="w")
        self.steps_var = tk.StringVar(value=str(DEFAULT_SIMULATION_STEPS))
        ttk.Entry(parent, textvariable=self.steps_var, width=10).pack(anchor="w", pady=(4, 4))
        ttk.Label(parent, text=f"1 step = {TIME_STEP_PS} ps half-cycle",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 10))

        ttk.Separator(parent).pack(fill="x", pady=6)
        ttk.Label(parent, text="Input stimulus (binary)", style="Panel.TLabel",
                  font=FONT_BOLD).pack(anchor="w", pady=(4, 4))
        ttk.Label(parent, text="Space-separated bits, one per step,\nor a single value to hold constant.",
                  style="Sub.TLabel", justify="left").pack(anchor="w", pady=(0, 6))

        self.inputs_frame = ttk.Frame(parent, style="Panel.TFrame")
        self.inputs_frame.pack(fill="x", pady=(0, 10))

        ttk.Button(parent, text="▶  Run Simulation", style="Accent.TButton",
                   command=self._run).pack(fill="x", pady=(10, 4))

        ttk.Label(parent, text="Parsed structure", style="Panel.TLabel",
                  font=FONT_BOLD).pack(anchor="w", pady=(14, 4))
        self.struct_box = scrolledtext.ScrolledText(
            parent, width=32, height=14, bg="#13161b", fg=TEXT,
            insertbackground=TEXT, font=FONT_MONO, relief="flat", wrap="word")
        self.struct_box.pack(fill="both", expand=True)
        self.struct_box.configure(state="disabled")

    def _build_result_panel(self, parent):
        self.fig = Figure(figsize=(9, 6), dpi=100, facecolor="white")
        self.ax = self.fig.add_subplot(111)
        self.ax.text(0.5, 0.5, "Run a simulation to see the waveform",
                      ha="center", va="center", fontsize=12, color="#999999")
        self.ax.axis("off")

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.pack(fill="x")
        NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.canvas.draw()

    # ── actions ──────────────────────────────────────────────────────────────
    def _browse(self):
        path = filedialog.askopenfilename(
            title="Choose a Verilog file", initialdir=str(HERE),
            filetypes=[("Verilog files", "*.v"), ("All files", "*.*")])
        if path:
            self.vfile = Path(path)
            self.file_var.set(self.vfile.name)
            self._load_file(self.vfile)

    def _load_file(self, path):
        try:
            code = path.read_text(encoding="utf-8")
            modules = list_modules(code)
            self.module_combo["values"] = modules or ["(default)"]
            chosen = self.module_var.get() if self.module_var.get() in modules else (modules[0] if modules else None)
            self.module_var.set(chosen or "")

            parsed = parse_verilog(code, simulate_module=chosen)
            self.parsed = parsed
            self._refresh_struct_box()
            self._refresh_input_fields()
            self.status.set(f"Loaded {path.name} — module '{parsed.get('module_name') or '?'}'.")
        except Exception as e:
            messagebox.showerror("Parse error", str(e))
            self.status.set(f"Error loading {path.name}: {e}")

    def _refresh_struct_box(self):
        p = self.parsed
        lines = [
            f"Module   : {p.get('module_name')}",
            f"Inputs   : {p['inputs']}",
            f"Outputs  : {p['outputs']}",
            f"Regs     : {p['regs']}",
            f"Wires    : {p['wires']}",
            "",
            "Widths:",
        ]
        for name, w in p["widths"].items():
            lines.append(f"  {name:<10} {w}-bit")
        lines.append("")
        lines.append(f"Assigns  : {len(p['assigns'])}")
        for out, expr in p["assigns"]:
            lines.append(f"  {out} = {expr}")
        lines.append("")
        lines.append(f"Always blocks: {len(p['always_blocks'])}")
        for blk in p["always_blocks"]:
            lines.append(f"  @({blk['sensitivity']})")

        self.struct_box.configure(state="normal")
        self.struct_box.delete("1.0", "end")
        self.struct_box.insert("1.0", "\n".join(lines))
        self.struct_box.configure(state="disabled")

    def _refresh_input_fields(self):
        for child in self.inputs_frame.winfo_children():
            child.destroy()
        self.signal_entries.clear()

        clocks = _find_clocks(self.parsed)
        non_clock = [n for n in self.parsed["inputs"] if n not in clocks]

        if clocks:
            ttk.Label(self.inputs_frame, text=f"Clock(s) auto-generated: {', '.join(sorted(clocks))}",
                      style="Sub.TLabel", wraplength=230, justify="left").pack(anchor="w", pady=(0, 6))

        if not non_clock:
            ttk.Label(self.inputs_frame, text="No stimulus needed — all inputs are clocks.",
                      style="Sub.TLabel", wraplength=230, justify="left").pack(anchor="w")
            return

        for name in non_clock:
            w = self.parsed["widths"].get(name, 1)
            row = ttk.Frame(self.inputs_frame, style="Panel.TFrame")
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=f"{name} [{w}-bit]", style="Panel.TLabel", width=14).pack(side="left")
            entry = ttk.Entry(row, width=14)
            entry.insert(0, "0" * w)
            entry.pack(side="left", fill="x", expand=True)
            self.signal_entries[name] = (entry, w)

    def _collect_user_inputs(self, steps):
        user_inputs = {}
        for name, (entry, w) in self.signal_entries.items():
            raw = entry.get().strip()
            if not raw:
                raise ValueError(f"'{name}' has no value.")
            parts = raw.split()
            vals = []
            for p in parts:
                if len(p) != w or not all(c in "01" for c in p):
                    raise ValueError(
                        f"'{name}': '{p}' is not a valid {w}-bit binary value.")
                vals.append(int(p, 2))
            if len(vals) == 1:
                vals = vals * steps
            while len(vals) < steps:
                vals.append(vals[-1])
            user_inputs[name] = vals[:steps]
        return user_inputs

    def _run(self):
        if not self.parsed:
            return
        try:
            steps = int(self.steps_var.get())
            if steps <= 0:
                raise ValueError("Steps must be a positive integer.")
            user_inputs = self._collect_user_inputs(steps)
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))
            self.status.set(f"Input error: {e}")
            return

        try:
            signals = simulate(self.parsed, steps=steps, user_inputs=user_inputs)
            draw_waveform(self.ax, signals, self.parsed["widths"], parsed=self.parsed,
                          title=f"Waveform — {self.vfile.name}", time_step_ps=TIME_STEP_PS)
            self.fig.tight_layout()
            self.canvas.draw()
            self.status.set(f"Simulated {steps} steps ({steps * TIME_STEP_PS} ps). "
                             f"{len(signals)} signals.")
        except Exception as e:
            messagebox.showerror("Simulation error", str(e))
            self.status.set(f"Simulation error: {e}")


if __name__ == "__main__":
    App().mainloop()
