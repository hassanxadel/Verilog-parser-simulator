from pathlib import Path

from parser import parse_verilog
from simulator import simulate
from waveform import plot_wave

_here = Path(__file__).resolve().parent
code = (_here / "test.v").read_text(encoding="utf-8")

parsed = parse_verilog(code)
signals = simulate(parsed)

plot_wave(signals)