"""
    python main.py                          # test.v, first module (default d_ff)
    python main.py path/to/file.v
    python main.py test.v mux2               # pick module when file has many
"""

import re
import sys
from pathlib import Path

from parser import parse_verilog
from simulator import (
    CLOCK_PERIOD_STEPS,
    DEFAULT_CLOCK_CYCLES,
    DEFAULT_SIMULATION_STEPS,
    TIME_STEP_PS,
    simulate,
    _find_clocks,
)
from waveform import plot_wave, signal_plot_order


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _to_bin(value, width):
    """Return value as a zero-padded binary string of exactly `width` digits."""
    return format(int(value) & ((1 << width) - 1), f'0{width}b')


def _from_bin(s):
    """Parse a binary string to int. Raises ValueError if not valid binary."""
    if not s or not all(c in '01' for c in s):
        raise ValueError(f"Not a binary string: '{s}'")
    return int(s, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Interactive input prompt  (binary only)
# ─────────────────────────────────────────────────────────────────────────────

def _prompt_inputs(input_names, clock_names, widths, steps):
    """
    Ask the user to enter binary values for every non-clock input signal.

    For each input the user types space-separated binary strings, one per step.
    e.g. for a 4-bit signal over 4 steps:  0000 0101 1010 1111
    A single binary value is repeated for all steps.
    """
    user_inputs = {}
    non_clock = [n for n in input_names if n not in clock_names]

    if not non_clock:
        return user_inputs

    print()
    print("=" * 60)
    print("  INPUT CONFIGURATION  (binary values only)")
    print("=" * 60)
    print(f"  Simulation steps : {steps}")
    print(f"  Clock signals    : {sorted(clock_names) or 'none'}")
    if clock_names:
        print(
            f"  Generated clock : toggles each step (half-cycle); {TIME_STEP_PS} ps per half-cycle, "
            f"{CLOCK_PERIOD_STEPS} steps = one full period ({2 * TIME_STEP_PS} ps), 50% duty."
        )
        if steps < CLOCK_PERIOD_STEPS:
            print(
                "                    [i] Simulation shorter than one full clock period — "
                f"use at least {CLOCK_PERIOD_STEPS} steps."
            )
    print()
    print("  Enter binary values (0s and 1s only), one per time step.")
    print("  A single value is repeated for all steps.")
    print("-" * 60)

    for name in non_clock:
        w      = widths.get(name, 1)
        maxbin = '1' * w
        hint   = f"  {name} [{w}-bit binary, e.g. {'0'*w}..{maxbin}] > "

        while True:
            raw = input(hint).strip()
            if not raw:
                print(f"    [!] Please enter at least one {w}-bit binary value.")
                continue

            parts = raw.split()
            vals = []
            parse_error = False

            for p in parts:
                # Must be exactly w binary digits
                if len(p) != w or not all(c in '01' for c in p):
                    print(f"    [!] '{p}' is not a valid {w}-bit binary value "
                          f"(must be exactly {w} digits of 0 or 1). Try again.")
                    parse_error = True
                    break
                vals.append(_from_bin(p))

            if parse_error:
                continue

            # Single value → repeat for all steps
            if len(vals) == 1:
                vals = vals * steps
                if steps > 1:
                    print(f"    [i] Single value given — repeated for all {steps} steps "
                          f"(waveform will be a flat line for {name}).")

            # Pad if too short
            if len(vals) < steps:
                last_bin = _to_bin(vals[-1], w)
                print(f"    [i] Only {len(vals)} value(s) given; "
                      f"padding with last value ({last_bin}) to fill {steps} steps.")
                while len(vals) < steps:
                    vals.append(vals[-1])

            # Truncate if too long
            if len(vals) > steps:
                print(f"    [i] {len(vals)} values given; using only the first {steps}.")
                vals = vals[:steps]

            user_inputs[name] = vals
            break

    print("=" * 60)
    return user_inputs


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    _here = Path(__file__).resolve().parent

    raw_tokens = sys.argv[1:]
    simulate_mod = None
    if raw_tokens:
        cand = raw_tokens[-1]
        if (
            re.fullmatch(r'[A-Za-z_]\w*', cand)
            and not cand.lower().endswith('.v')
            and '/' not in cand
            and '\\' not in cand
            and not re.fullmatch(r'[A-Za-z]:', cand)
        ):
            simulate_mod = cand
            raw_tokens = raw_tokens[:-1]

    if raw_tokens:
        vfile = Path(" ".join(raw_tokens))
        if not vfile.is_absolute():
            vfile = _here / vfile
    else:
        vfile = _here / "test.v"

    if not vfile.exists():
        print(f"[ERROR] File not found: {vfile}")
        sys.exit(1)

    print(f"\n[INFO]  Loading: {vfile.name}")
    code = vfile.read_text(encoding="utf-8")

    try:
        parsed = parse_verilog(code, simulate_module=simulate_mod)
    except ValueError as e:
        print(f"[ERROR]  {e}")
        sys.exit(1)

    print("\n--- Parsed structure -------------------------------------------")
    if parsed.get("module_name"):
        print(f"  Module  : {parsed['module_name']}")
    print(f"  Inputs  : {parsed['inputs']}")
    print(f"  Outputs : {parsed['outputs']}")
    print(f"  Regs    : {parsed['regs']}")
    print(f"  Wires   : {parsed['wires']}")
    print(f"  Assigns : {parsed['assigns']}")
    print(f"  Always  : {len(parsed['always_blocks'])} block(s)")

    clock_hint = _find_clocks(parsed)
    print()
    if clock_hint:
        span_ps = DEFAULT_SIMULATION_STEPS * TIME_STEP_PS
        print(
            f"  [i] Each simulation step = one half-cycle = {TIME_STEP_PS} ps "
            f"(two steps = one full clock = {2 * TIME_STEP_PS} ps)."
        )
        print(
            f"      Default {DEFAULT_SIMULATION_STEPS} steps = {span_ps} ps "
            f"= {DEFAULT_CLOCK_CYCLES} full clock cycles."
        )
        print(
            "      Step count = 2 × (number of full clock cycles). "
            "Timeline length (ps) = steps × (half-cycle in ps)."
        )

    print()
    while True:
        raw = input(
            f"  How many time steps to simulate? [default: {DEFAULT_SIMULATION_STEPS}] > "
        ).strip()
        if raw == "":
            steps = DEFAULT_SIMULATION_STEPS
            break
        if raw.isdigit() and int(raw) > 0:
            steps = int(raw)
            break
        print("  [!] Please enter a positive integer.")

    clock_names = _find_clocks(parsed)
    user_inputs = _prompt_inputs(parsed["inputs"], clock_names,
                                 parsed["widths"], steps)

    signals = simulate(parsed, steps=steps, user_inputs=user_inputs)

    # ── Print signal table in binary ─────────────────────────────────────────
    widths = parsed["widths"]
    print("\n--- Simulated signals (binary) ---------------------------------")
    col_w = max(len(n) for n in signals) + 2
    row_names = signal_plot_order(parsed, signals)

    hdr = "  ".join(str(t * TIME_STEP_PS) for t in range(steps))
    print(" " * (col_w + 2) + hdr)
    print("       (time in ps; inputs top / outputs bottom in waveform viewer)")
    for name in reversed(row_names):
        vals = signals[name]
        w    = widths.get(name, 1)
        row  = "  ".join(_to_bin(v, w) for v in vals)
        print(f"  {name:<{col_w}}{row}")

    print("\n[INFO]  Opening waveform window ...")
    plot_wave(
        signals,
        parsed["widths"],
        parsed=parsed,
        title=f"Waveform - {vfile.name}",
        time_step_ps=TIME_STEP_PS,
    )


if __name__ == "__main__":
    main()
