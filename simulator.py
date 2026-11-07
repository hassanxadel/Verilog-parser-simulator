import re

_STIMULUS_ROWS = [
    [0, 1, 1, 0, 1, 0, 1, 1],
    [1, 1, 0, 0, 1, 1, 0, 0],
    [0, 1, 0, 1, 0, 1, 0, 1],
    [1, 0, 1, 0, 1, 0, 1, 0],
]


def _stimulus_for_input(index, steps):
    row = _STIMULUS_ROWS[index % len(_STIMULUS_ROWS)]
    if steps <= len(row):
        return row[:steps]
    return [row[i % len(row)] for i in range(steps)]


# Auto-generated CLK: **coarse-grained time** so waveforms stay readable.
# One simulation step = one half-cycle on the timeline (100 ps). Full period = 200 ps (2 steps).
#   t=0,2,4,... -> LOW   ;   t=1,3,5,... -> HIGH   (posedge at odd t)
TIME_STEP_PS = 100
CLOCK_HALF_PERIOD_STEPS = 1
CLOCK_PERIOD_STEPS = 2

DEFAULT_CLOCK_CYCLES = 10
DEFAULT_SIMULATION_STEPS = CLOCK_PERIOD_STEPS * DEFAULT_CLOCK_CYCLES  # e.g. 20 coarse steps


def _clock_signal(steps):
    return [t % 2 for t in range(steps)]


def _depth_adjust(ch, depth):
    if ch in '([':
        return depth + 1
    if ch in ')]':
        return depth - 1
    return depth


def _convert_verilog_ternary(expr):
    """
    Recursively rewrite Verilog ``cond ? hi : lo`` → Python ``(hi if cond else lo)``.
    Uses the **first** ``:`` at depth 0 (Verilog right-associative ``?:``).
    """
    expr = expr.strip()
    if '?' not in expr or ':' not in expr:
        return expr

    colon_pos = -1
    depth = 0
    for i, ch in enumerate(expr):
        depth = _depth_adjust(ch, depth)
        if ch == ':' and depth == 0:
            colon_pos = i
            break

    if colon_pos < 0:
        return expr

    q_pos = -1
    depth = 0
    for i in range(colon_pos - 1, -1, -1):
        ch = expr[i]
        if ch in ')]':
            depth += 1
        elif ch in '([':
            depth -= 1
        elif ch == '?' and depth == 0:
            q_pos = i
            break

    if q_pos < 0:
        return expr

    cond = _convert_verilog_ternary(expr[:q_pos].strip())
    thn  = _convert_verilog_ternary(expr[q_pos + 1:colon_pos].strip())
    els  = _convert_verilog_ternary(expr[colon_pos + 1 :].strip())
    return f"(({thn}) if ({cond}) else ({els}))"


def _normalize_expr(expr):
    expr = expr.replace('<=', ' <= ')
    # Strip sized literals first so ``2'b10`` does not confuse ``?:`` scan.
    expr = re.sub(r"\d+'b([01]+)", lambda m: str(int(m.group(1), 2)), expr)
    expr = re.sub(r"\d+'h([0-9a-fA-F]+)", lambda m: str(int(m.group(1), 16)), expr)
    expr = re.sub(r"\d+'d(\d+)", lambda m: m.group(1), expr)
    expr = _convert_verilog_ternary(expr)

    expr = re.sub(r'&&', ' and ', expr)
    expr = re.sub(r'\|\|', ' or ', expr)
    expr = re.sub(r'(?<![=<>!])&(?!=)', ' & ', expr)
    expr = re.sub(r'(?<![|])\|(?!\|)', ' | ', expr)
    expr = re.sub(r'\^', ' ^ ', expr)
    expr = re.sub(r'~', ' ~', expr)
    expr = re.sub(r'!(?!=)', ' not ', expr)
    return expr


def eval_expr(expr, values):
  
    expr = _normalize_expr(expr)

    for var in sorted(values.keys(), key=len, reverse=True):
        expr = re.sub(rf'\b{re.escape(var)}\b', str(int(values[var])), expr)
    try:
        result = eval(expr)
  
        return int(result)
    except Exception:
        return 0


def _mask(v, w):
    """Mask integer ``v`` to ``w`` bits (unsigned wrap)."""
    if w <= 0:
        return 0
    return int(v) & ((1 << w) - 1)


def _distribute_concat(targets, value, widths, current, next_state, blocking):

    sig_widths = [widths.get(t, 1) for t in targets]
    total = sum(sig_widths)

    value = value & ((1 << total) - 1)

    bit_pos = 0
    for sig, w in zip(reversed(targets), reversed(sig_widths)):
        mask = (1 << w) - 1
        part = (value >> bit_pos) & mask
        bit_pos += w
        if blocking:
            current[sig] = part
            next_state[sig] = part
        else:
            next_state[sig] = part


def _exec_statements(stmts, current, next_state, widths=None):
   
    if widths is None:
        widths = {}
    for stmt in stmts:
        t = stmt["type"]

        if t in ("nonblocking", "blocking"):
            val = eval_expr(stmt["expr"], current)

            if stmt.get("concat"):
                targets = stmt["target"]
                _distribute_concat(targets, val, widths, current, next_state,
                                   blocking=(t == "blocking"))
            elif t == "nonblocking":
                tw = widths.get(stmt["target"], 1)
                next_state[stmt["target"]] = _mask(val, tw)
            else:
                tw = widths.get(stmt["target"], 1)
                val = _mask(val, tw)
                current[stmt["target"]] = val
                next_state[stmt["target"]] = val

        elif t == "if":
            cond = eval_expr(stmt["condition"], current)
            branch = stmt["true_branch"] if cond else stmt["false_branch"]
            _exec_statements(branch, current, next_state, widths)

        elif t == "case":
            sel_val = eval_expr(stmt["selector"], current)
            matched = False
            for item in stmt["items"]:
                if item["value"] == "default":
                    continue
                item_val = eval_expr(item["value"], current)
                if sel_val == item_val:
                    _exec_statements(item["stmts"], current, next_state, widths)
                    matched = True
                    break
            if not matched:
                for item in stmt["items"]:
                    if item["value"] == "default":
                        _exec_statements(item["stmts"], current, next_state, widths)
                        break


def _topo_sort_assigns(assigns):
   
    output_names = {a[0] for a in assigns}
    order = []
    remaining = list(assigns)
    resolved = set()

    max_passes = len(assigns) + 1
    for _ in range(max_passes):
        if not remaining:
            break
        progress = False
        still_remaining = []
        for out, expr in remaining:
            deps = set(re.findall(r'\b([A-Za-z_]\w*)\b', expr))
            unresolved_deps = (deps & output_names) - resolved
            if not unresolved_deps:
                order.append((out, expr))
                resolved.add(out)
                progress = True
            else:
                still_remaining.append((out, expr))
        remaining = still_remaining
        if not progress:
            order.extend(remaining)
            break

    return order

def simulate(parsed, steps=10, user_inputs=None):

    signals = {}
    non_clock_idx = 0
    clock_names = _find_clocks(parsed)

    for name in parsed["inputs"]:
        if name in clock_names:
            signals[name] = _clock_signal(steps)
        elif user_inputs and name in user_inputs:
            vals = list(user_inputs[name])
            while len(vals) < steps:
                vals.append(vals[-1] if vals else 0)
            signals[name] = vals[:steps]
        else:
            signals[name] = _stimulus_for_input(non_clock_idx, steps)
            non_clock_idx += 1

    reg_state = {name: 0 for name in parsed.get("regs", [])}

    sorted_assigns = _topo_sort_assigns(parsed.get("assigns", []))

    for t in range(steps):
       
        current = {}
        for name, vals in signals.items():
            if len(vals) > t:
                current[name] = vals[t]
       
        current.update(reg_state)

        for out, expr in sorted_assigns:
            val = eval_expr(expr, current)
            ow = parsed.get("widths", {}).get(out, 1)
            val = _mask(val, ow)
            current[out] = val
            if out not in signals:
                signals[out] = []
            signals[out].append(val)

        next_state = dict(reg_state)

        for block in parsed.get("always_blocks", []):
            clk = block.get("clock")
            edge = block.get("edge")

            if clk:
                clk_now = current.get(clk, 0)
                # No transition at t==0: initial samples are initial conditions, not edges.
                if t == 0:
                    clk_prev = clk_now
                else:
                    clk_prev = signals.get(clk, [0])[t - 1]
                rising  = (clk_prev == 0 and clk_now == 1)
                falling = (clk_prev == 1 and clk_now == 0)

                if (edge == "posedge" and rising) or (edge == "negedge" and falling):
                    _exec_statements(block["body"], dict(current), next_state,
                                     parsed.get("widths", {}))
            else:
                _exec_statements(block["body"], dict(current), next_state,
                                 parsed.get("widths", {}))

        reg_state = {
            k: _mask(v, parsed.get("widths", {}).get(k, 1))
            for k, v in next_state.items()
        }
        for name, val in reg_state.items():
            if name not in signals:
                signals[name] = []
            signals[name].append(val)

    for name in signals:
        while len(signals[name]) < steps:
            signals[name].append(signals[name][-1] if signals[name] else 0)

    return signals


def _find_clocks(parsed):
 
    clocks = set()
    for block in parsed.get("always_blocks", []):
        if block.get("clock"):
            clocks.add(block["clock"])
    return clocks
