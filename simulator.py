import re

_STIMULUS_ROWS = [
    [0, 1, 1, 0, 1],
    [1, 1, 0, 0, 1],
    [0, 1, 0, 1, 0],
    [1, 0, 1, 0, 1],
]


def _stimulus_for_input(index, steps):
    row = _STIMULUS_ROWS[index % len(_STIMULUS_ROWS)]
    if steps <= len(row):
        return row[:steps]
    return [row[i % len(row)] for i in range(steps)]


def eval_expr(expr, values):
    expr = expr.replace('&', ' and ')
    expr = expr.replace('|', ' or ')
    expr = expr.replace('^', ' ^ ')
    expr = expr.replace('~', ' not ')

    for var, val in values.items():
        expr = re.sub(rf'\b{var}\b', str(val), expr)

    return int(eval(expr))


def simulate(parsed, steps=5):
    signals = {}
    for i, name in enumerate(parsed["inputs"]):
        signals[name] = _stimulus_for_input(i, steps)

    for t in range(steps):
        current = {k: signals[k][t] for k in signals if len(signals[k]) > t}

        for out, expr in parsed["assigns"]:
            value = eval_expr(expr, current)

            if out not in signals:
                signals[out] = []

            signals[out].append(value)
            current[out] = value  

    return signals