import matplotlib

for _backend in ("TkAgg", "Qt5Agg", "QtAgg"):
    try:
        matplotlib.use(_backend, force=True)
        break
    except Exception:
        continue

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker


_COLOURS = [
    "#2196F3",  # blue
    "#4CAF50",  # green
    "#F44336",  # red
    "#FF9800",  # orange
    "#9C27B0",  # purple
    "#00BCD4",  # cyan
    "#E91E63",  # pink
    "#795548",  # brown
]

_TRACE_HEIGHT = 0.8   # height of the HIGH portion within each lane
_ROW_SPACING  = 2.2   # vertical distance between lane baselines


def _to_bin(value, width):
    """Return value as a zero-padded binary string of exactly `width` digits."""
    return format(int(value) & ((1 << width) - 1), f'0{width}b')


def signal_plot_order(parsed, signals):
    """
    Build matplotlib trace order so **outputs sit at the bottom** and **inputs
    at the top** (EDA-style waveform viewer).

    In this plot loop, lane index ``i`` increases upward from the diagram bottom:
    smaller ``i`` = lower on screen.  So declare **outputs first**, then inputs.
    """
    keys = set(signals.keys())

    inp = list(parsed.get("inputs", []))
    out = list(parsed.get("outputs", []))

    seen = set()
    ordered_out = []

    for name in out:
        if name in keys:
            ordered_out.append(name)
            seen.add(name)

    for name in keys:
        if name not in seen and name not in inp:
            ordered_out.append(name)
            seen.add(name)

    ordered_in = [n for n in inp if n in keys]

    full = ordered_out + ordered_in
    for name in signals:
        if name not in full:
            full.append(name)
    return full


def _masked_scale(value, width, base):
    """
    Scale an integer signal value to a y-coordinate within its lane.

    The value is first masked to `width` bits so arithmetic overflow
    never pushes the trace outside the lane boundaries.
    For 1-bit signals: 0 → base,  1 → base + _TRACE_HEIGHT
    For N-bit signals: proportional between base and base + _TRACE_HEIGHT
    """
    maxval = (1 << width) - 1
    masked = int(value) & maxval
    if maxval == 0:
        return base
    return base + (masked / maxval) * _TRACE_HEIGHT


def draw_waveform(
    ax,
    signals,
    widths=None,
    parsed=None,
    title="Digital Waveform",
    time_step_ps=None,
):
    """
    Draw all signals as colour-coded digital step waveforms onto an existing
    matplotlib Axes. All annotations show binary values.

    This is the shared rendering core used both by ``plot_wave`` (standalone
    popup window) and by GUIs that embed a matplotlib canvas directly.

    Parameters
    ----------
    ax      : matplotlib.axes.Axes — target axes to draw on (cleared first)
    signals : dict  { name: [int, ...] }
    widths  : dict  { name: int }  — bit-widths from the parser
    parsed  : dict or None — if given, traces are stacked with **inputs on top**
              and **outputs on the bottom** (like typical wave viewers).
    title   : str
    time_step_ps : int or None — if set, x-axis is time in ps (step i → i * time_step_ps)
    """
    if widths is None:
        widths = {}

    ax.clear()

    names = signal_plot_order(parsed, signals) if parsed is not None else list(signals.keys())
    n     = len(names)
    steps = max(len(v) for v in signals.values())

    patches         = []
    ytick_positions = []
    ytick_labels    = []

    for i, name in enumerate(names):
        values = list(signals[name])
        colour = _COLOURS[i % len(_COLOURS)]
        base   = i * _ROW_SPACING
        w      = widths.get(name, 1)

        # Pad short signals by holding the last value
        if len(values) < steps:
            values += [values[-1]] * (steps - len(values))

        # Build the step trace (one extra point to close the last step)
        xs     = list(range(steps + 1))
        scaled = [_masked_scale(v, w, base) for v in values]
        ys     = scaled + [scaled[-1]]

        # Draw the stepped trace
        ax.step(xs, ys, where='post', color=colour, linewidth=2.0)

        # Faint fill under the trace
        ax.fill_between(xs, base, ys, step='post', color=colour, alpha=0.10)

        # Draw the LOW baseline so even a 0-valued signal is visible
        ax.hlines(base, 0, steps, colors=colour, linewidth=0.6,
                  linestyles='dotted', alpha=0.4)

        # Binary annotation inside each step cell
        # Only show if cells are wide enough (skip when > 30 steps)
        if steps <= 30:
            for t in range(steps):
                bin_label = _to_bin(values[t], w)
                ax.text(t + 0.5, base + _TRACE_HEIGHT * 0.5,
                        bin_label,
                        ha='center', va='center',
                        fontsize=max(6, 9 - w),   # shrink font for wide buses
                        color=colour,
                        alpha=0.85,
                        fontfamily='monospace',
                        fontweight='bold')

        ytick_positions.append(base + _TRACE_HEIGHT * 0.5)
        ytick_labels.append(name)
        patches.append(mpatches.Patch(color=colour, label=name))

    # Legend reads top-down like the waveform (inputs listed first → top traces)
    legend_handles = list(reversed(patches))

    # ── Axes formatting ───────────────────────────────────────────────────────
    ax.set_yticks(ytick_positions)
    ax.set_yticklabels(ytick_labels, fontsize=10, fontweight='bold')
    ax.set_ylim(-0.6, n * _ROW_SPACING)

    # Force integer x-axis ticks (one per time step)
    ax.set_xlim(0, steps)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True, steps=[1, 2, 4, 5, 10]))
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: int(x)))
    ax.set_xticks(range(steps + 1))
    if time_step_ps is not None:
        ax.set_xticklabels(
            [str(int(t * time_step_ps)) for t in range(steps + 1)],
            fontsize=9,
        )
        ax.set_xlabel(
            f"Time (ps);  {time_step_ps} ps per step (half-cycle); "
            f"full clock period = {2 * time_step_ps} ps",
            fontsize=10,
        )
    else:
        ax.set_xticklabels([str(t) for t in range(steps + 1)], fontsize=9)
        ax.set_xlabel("Time step", fontsize=10)
    ax.set_title(title, fontsize=13, fontweight='bold', pad=10)

    # Vertical grid lines at every time step boundary
    for t in range(steps + 1):
        ax.axvline(t, color='#bbbbbb', linewidth=0.7, zorder=0)

    # Horizontal separator between lanes
    for i in range(n + 1):
        ax.axhline(i * _ROW_SPACING - 0.35, color='#dddddd',
                   linewidth=1.0, zorder=0)

    ax.legend(handles=legend_handles, loc='upper right', fontsize=8,
              framealpha=0.8, edgecolor='#cccccc')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(left=False)


def plot_wave(
    signals,
    widths=None,
    parsed=None,
    title="Digital Waveform",
    time_step_ps=None,
):
    """Open a standalone matplotlib window and draw the waveform (CLI mode)."""
    names = signal_plot_order(parsed, signals) if parsed is not None else list(signals.keys())
    n     = len(names)
    steps = max(len(v) for v in signals.values())

    fig_w = max(12, steps * 1.3)
    fig_h = max(4,  n * 1.4 + 1.5)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    draw_waveform(ax, signals, widths=widths, parsed=parsed,
                  title=title, time_step_ps=time_step_ps)

    plt.tight_layout()
    plt.show(block=True)
