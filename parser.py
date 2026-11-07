import re


def _eval_width(msb_expr, lsb_expr, params):
   
    if msb_expr is None or lsb_expr is None:
        return 1
    try:
 
        def _sub(expr):
            for name, val in sorted(params.items(), key=lambda x: -len(x[0])):
                expr = re.sub(rf'\b{re.escape(name)}\b', str(val), expr)
            return expr
        msb = int(eval(_sub(msb_expr.strip())))  
        lsb = int(eval(_sub(lsb_expr.strip())))  
        return abs(msb - lsb) + 1
    except Exception:
        return 1


def _parse_ansi_ports(code, params):
    """
    Parse ANSI-style port declarations from the module header port list.

    Handles patterns like:
        module M #(parameter w=4) (
            input  [w-1:0] a, b,
            input          cin,
            input  [1:0]   control,
            output reg [w-1:0] d,
            output reg         cout
        );

    Returns three lists of (name, width) tuples: inputs, outputs, regs.
    """
    inputs  = []
    outputs = []
    regs    = []

    # Extract the module port list: everything between the first ( and matching )
    m = re.search(r'module\s+\w+\s*(?:#\s*\([^)]*\)\s*)?\(', code)
    if not m:
        return inputs, outputs, regs

    start = m.end()
    depth = 1
    i = start
    while i < len(code) and depth > 0:
        if code[i] == '(':
            depth += 1
        elif code[i] == ')':
            depth -= 1
        i += 1
    port_list = code[start:i-1]

    # Each port declaration inside the list is separated by commas, but a
    # single declaration can cover multiple names: "input [3:0] a, b"
    # We split on commas that are NOT inside brackets.
    # Strategy: scan token by token, resetting direction/width on keywords.
    current_dir   = None
    current_width = 1
    is_reg        = False

    # Tokenise: split on commas while tracking bracket depth
    tokens = _split_port_tokens(port_list)

    for token in tokens:
        token = token.strip()
        if not token:
            continue

        # Check if this token starts a new direction keyword
        dir_m = re.match(
            r'^(input|output|inout)\s+'
            r'(?:(?:reg|wire)\s+)?'
            r'(?:\[([^\]]+):([^\]]+)\]\s+)?'
            r'(\w+)$',
            token
        )
        if dir_m:
            current_dir   = dir_m.group(1)
            is_reg        = bool(re.search(r'\breg\b', token))
            current_width = _eval_width(dir_m.group(2), dir_m.group(3), params)
            name          = dir_m.group(4)
        else:
            # May be just a name continuing the previous direction
            name_m = re.match(r'^(\w+)$', token)
            if name_m:
                name = name_m.group(1)
            else:
                # Try full declaration without direction (continuation)
                full_m = re.match(
                    r'(?:(input|output|inout)\s+)?'
                    r'(?:(?:reg|wire)\s+)?'
                    r'(?:\[([^\]]+):([^\]]+)\]\s+)?'
                    r'(\w+)$',
                    token
                )
                if not full_m:
                    continue
                if full_m.group(1):
                    current_dir   = full_m.group(1)
                    is_reg        = bool(re.search(r'\breg\b', token))
                    current_width = _eval_width(full_m.group(2), full_m.group(3), params)
                name = full_m.group(4)

        if not current_dir or not name:
            continue

        if current_dir == 'input':
            inputs.append((name, current_width))
        elif current_dir in ('output', 'inout'):
            outputs.append((name, current_width))
            if is_reg:
                regs.append((name, current_width))

    return inputs, outputs, regs


def _split_into_modules(code):
    """
    Return [(module_name, source_text)] for every ``module … endmodule`` pair
    in order.  Non-overlapping; uses ``endmodule`` token only.
    """
    pieces = []
    for m in re.finditer(r'\bmodule\s+(\w+)\b', code):
        name  = m.group(1)
        start = m.start()
        em    = re.search(r'\bendmodule\b', code[m.end():])
        if not em:
            break
        end_abs = m.end() + em.end()
        pieces.append((name, code[start:end_abs]))
    return pieces


def _split_port_tokens(port_list):
    """
    Split a port list string on commas, but only at depth 0 (not inside brackets).
    Returns a list of token strings.
    """
    tokens = []
    depth  = 0
    start  = 0
    for i, ch in enumerate(port_list):
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        elif ch == ',' and depth == 0:
            tokens.append(port_list[start:i])
            start = i + 1
    tokens.append(port_list[start:])
    return tokens


def list_modules(code):
    """Return the names of every ``module ... endmodule`` block in `code`, in order."""
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'//[^\n]*', '', code)
    return [name for name, _ in _split_into_modules(code)]


def parse_verilog(code, simulate_module=None):
    """Parse Verilog. If several ``module … endmodule`` blocks exist,
    simulate **simulate_module**, or otherwise the **first** module."""

    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'//[^\n]*', '', code)

    mods = _split_into_modules(code)
    simulated_name = None
    if mods:
        if simulate_module:
            fragment = None
            for nm, frag in mods:
                if nm == simulate_module:
                    fragment = frag
                    simulated_name = nm
                    break
            if fragment is None:
                avail = ', '.join(n for n, _ in mods)
                raise ValueError(
                    f"Module '{simulate_module}' not defined in this file."
                    f" Available: {avail}"
                )
            code = fragment
        else:
            simulated_name = mods[0][0]
            code = mods[0][1]

    params = {}
    for pm in re.finditer(r'\bparameter\b\s+(\w+)\s*=\s*(\d+)', code):
        params[pm.group(1)] = int(pm.group(2))
    
    for pm in re.finditer(r'#\s*\(\s*parameter\s+(\w+)\s*=\s*(\d+)', code):
        params[pm.group(1)] = int(pm.group(2))

   
    def _parse_decls(keyword, src=None):
        if src is None:
            src = code
        result = []
        pattern = rf'{keyword}\s+(?:\[([^\]]+):([^\]]+)\]\s+)?(.+?);'
        for m in re.finditer(pattern, src):
            msb_expr, lsb_expr, names_str = m.group(1), m.group(2), m.group(3)
            width = _eval_width(msb_expr, lsb_expr, params)
            for name in names_str.split(','):
                name = name.strip()
                if name:
                    result.append((name, width))
        return result

    
    code_norm = re.sub(r'\boutput\s+reg\b',   'output', code)
    code_norm = re.sub(r'\boutput\s+wire\b',  'output', code_norm)
    code_norm = re.sub(r'\binput\s+wire\b',   'input',  code_norm)
    code_norm = re.sub(r'\binput\s+reg\b',    'input',  code_norm)

    # ── Body-style declarations (each ends with ;) ────────────────────────────
    inputs  = _parse_decls('input',  code_norm)
    outputs = _parse_decls('output', code_norm)
    wires   = _parse_decls('wire',   code)
    regs    = _parse_decls('reg',    code)

    # ── ANSI-style port declarations inside the module(...) header ────────────
    # e.g.  module M #(parameter w=4) ( input [w-1:0] a, b,  output reg cout );
    # These are comma-separated inside the port list, not terminated by ;
    ansi_inputs, ansi_outputs, ansi_regs = _parse_ansi_ports(code, params)
    # Merge: body declarations take priority (they are more explicit)
    existing_names = {n for n, _ in inputs + outputs + regs + wires}
    inputs  += [(n, w) for n, w in ansi_inputs  if n not in existing_names]
    outputs += [(n, w) for n, w in ansi_outputs if n not in existing_names]
    regs    += [(n, w) for n, w in ansi_regs    if n not in existing_names]

    assigns = []
    for m in re.finditer(r'assign\s+(\w+)\s*=\s*(.+?);', code):
        assigns.append((m.group(1), m.group(2).strip()))

    always_blocks = _parse_always_blocks(code)

    widths = {}
    for name, w in inputs + outputs + wires + regs:
        widths[name] = w

    return {
        "module_name":   simulated_name,
        "inputs":        [n for n, _ in inputs],
        "outputs":       [n for n, _ in outputs],
        "wires":         [n for n, _ in wires],
        "regs":          [n for n, _ in regs],
        "widths":        widths,
        "assigns":       assigns,
        "always_blocks": always_blocks,
    }


def _parse_always_blocks(code):
 
    blocks = []
    for m in re.finditer(r'always\s*@\s*\(([^)]+)\)', code):
        sensitivity = m.group(1).strip()
        clock = None
        edge  = None

        edge_m = re.match(r'(posedge|negedge)\s+(\w+)', sensitivity)
        if edge_m:
            edge  = edge_m.group(1)
            clock = edge_m.group(2)

        body_start = m.end()
        body_text, _ = _extract_block(code, body_start)
        stmts = _parse_statements(body_text)

        blocks.append({
            "sensitivity": sensitivity,
            "clock":       clock,
            "edge":        edge,
            "body":        stmts,
        })
    return blocks


def _extract_block(code, start):
    i = start

    while i < len(code) and code[i] in ' \t\n\r':
        i += 1

    if i < len(code) and code[i:i+5] == 'begin':

        depth = 1
        j = i + 5
        while j < len(code) and depth > 0:
            if code.startswith('begin', j):
                depth += 1
                j += 5
            elif code.startswith('endmodule', j):
                # Do not confuse ``end`` inside ``endmodule`` with ``end``.
                j += 9
            elif code.startswith('endcase', j):
                j += 7
            elif code.startswith('end', j):
                depth -= 1
                j += 3
            else:
                j += 1
        return code[i + 5 : j - 3].strip(), j
    else:

        end = code.find(';', i)
        if end == -1:
            return code[i:].strip(), len(code)
        return code[i:end+1].strip(), end + 1


def _parse_statements(text):
 
    stmts = []
    text = text.strip()
    if not text:
        return stmts

    i = 0
    while i < len(text):

        while i < len(text) and text[i] in ' \t\n\r':
            i += 1
        if i >= len(text):
            break

        if text[i:i+2] == 'if':
            cond_m = re.match(r'if\s*\(([^)]+)\)', text[i:])
            if cond_m:
                cond = cond_m.group(1).strip()
                after_cond = i + cond_m.end()
                true_text, after_true = _extract_block(text, after_cond)
                true_stmts = _parse_statements(true_text)

                rest = text[after_true:].lstrip()
                false_stmts = []
                if rest.startswith('else'):
                    else_start = after_true + text[after_true:].index('else') + 4
                    false_text, after_false = _extract_block(text, else_start)
                    false_stmts = _parse_statements(false_text)
                    i = after_false
                else:
                    i = after_true

                stmts.append({
                    "type":        "if",
                    "condition":   cond,
                    "true_branch": true_stmts,
                    "false_branch": false_stmts,
                })
                continue

        if text[i:i+4] == 'case':
            case_m = re.match(r'case\s*\(([^)]+)\)', text[i:])
            if case_m:
                sel = case_m.group(1).strip()
                after_sel = i + case_m.end()
                end_idx = text.find('endcase', after_sel)
                if end_idx == -1:
                    end_idx = len(text)
                case_body = text[after_sel:end_idx]
                items = _parse_case_items(case_body)
                stmts.append({
                    "type":     "case",
                    "selector": sel,
                    "items":    items,
                })
                i = end_idx + len('endcase')
                continue

        semi = text.find(';', i)
        if semi == -1:
            break
        stmt_text = text[i:semi+1].strip()

        concat_nb = re.match(r'\{([^}]+)\}\s*<=\s*(.+);', stmt_text)
        concat_b  = re.match(r'\{([^}]+)\}\s*=\s*(.+);',  stmt_text)
        nb_m = re.match(r'(\w+)\s*<=\s*(.+);', stmt_text)
        b_m  = re.match(r'(\w+)\s*=\s*(.+);',  stmt_text)

        if concat_nb or concat_b:
            m = concat_nb or concat_b
            targets = [t.strip() for t in m.group(1).split(',')]
            stmts.append({
                "type":    "nonblocking" if concat_nb else "blocking",
                "target":  targets,        # list signals MSB-first
                "expr":    m.group(2).strip(),
                "concat":  True,
            })
        elif nb_m:
            stmts.append({
                "type":   "nonblocking",
                "target": nb_m.group(1),
                "expr":   nb_m.group(2).strip(),
            })
        elif b_m:
            stmts.append({
                "type":   "blocking",
                "target": b_m.group(1),
                "expr":   b_m.group(2).strip(),
            })
        i = semi + 1

    return stmts


def _parse_case_items(body):

    items = []
    i = 0
    body = body.strip()

    while i < len(body):

        while i < len(body) and body[i] in ' \t\n\r':
            i += 1
        if i >= len(body):
            break

        colon = body.find(':', i)
        if colon == -1:
            break

        val = body[i:colon].strip()
        if not val:
            i = colon + 1
            continue

        item_text, end = _extract_block(body, colon + 1)
        inner = _parse_statements(item_text)
        items.append({"value": val, "stmts": inner})
        i = end

    return items
