Verilog Waveform Parser and Simulator
Full Project Documentation


Faculty of Engineering, Ain Shams University
Department of Electronics and Communications Engineering


---


TABLE OF CONTENTS

1.  Introduction
2.  Project Objectives
3.  System Overview
4.  Project File Structure
5.  How the System Works — Pipeline Description
6.  Supported Verilog Constructs
7.  Installation and Requirements
8.  How to Run the Program
9.  Source Code Documentation
    9.1  main.py — Entry Point and User Interface
    9.2  parser.py — Verilog Parser
    9.3  simulator.py — Simulation Engine
    9.4  waveform.py — Waveform Visualizer
    9.5  test.v — Sample Verilog Design (4-bit ALU)
10. Internal Data Structures
11. Example Simulation Session
12. Screenshots
13. Known Limitations
14. Future Improvements
15. Conclusion


---


1. INTRODUCTION

This project is a Python-based Electronic Design Automation (EDA) tool that reads a Verilog hardware description file, simulates the described digital circuit over a user-defined number of time steps, and displays the resulting signal behavior as a digital timing waveform in a graphical popup window.

The motivation behind this project is to demonstrate the fundamental concepts that underlie professional hardware simulation tools such as ModelSim and Icarus Verilog, but in a simplified, readable, and educational form. A user can write a Verilog module describing a digital circuit, paste it into the test.v file, run the program, enter the input values interactively in the terminal, and immediately see the waveform of all signals.

The tool supports both combinational logic (assign statements and always @(*) blocks) and sequential logic (always @(posedge clk) flip-flop style blocks), multi-bit bus signals, arithmetic operations, case statements, and if/else constructs.


---


2. PROJECT OBJECTIVES

The main objectives of this project are:

    - To parse a simplified subset of the Verilog hardware description language using Python regular expressions and produce a structured internal representation of the circuit.

    - To simulate the behavior of the parsed circuit over discrete time steps, evaluating combinational expressions and executing sequential always blocks in the correct order.

    - To allow the user to define the input stimulus interactively through the terminal, with proper validation of values based on each signal's bit-width.

    - To visualize the simulated signal transitions as a digital timing waveform using the matplotlib library, with each signal displayed in its own color-coded lane.

    - To serve as an educational demonstration of how hardware simulators work at a conceptual level.


---


3. SYSTEM OVERVIEW

The system is organized as a four-stage pipeline:

    Stage 1 — Parsing:
    The Verilog source file is read as plain text. The parser extracts all port declarations, signal widths, assign statements, and always blocks using regular expressions. The result is a structured Python dictionary.

    Stage 2 — User Input:
    The program reads the parsed input signal names and their bit-widths, then prompts the user in the terminal to enter values for each non-clock input signal. Clock signals are automatically generated.

    Stage 3 — Simulation:
    The simulation engine iterates over each time step. At every step it evaluates combinational assign expressions in dependency order, then executes any always blocks (firing sequential blocks only on clock edges). The result is a dictionary mapping every signal name to a list of values, one per time step.

    Stage 4 — Visualization:
    The waveform module takes the signal dictionary and renders each signal as a stepped trace in a matplotlib window. Each signal gets its own color, lane, and value annotations.

The data flow through the pipeline is:

    test.v (text file)
         |
         v
    parse_verilog()   -->   parsed dict (inputs, outputs, widths, assigns, always blocks)
         |
         v
    _prompt_inputs()  -->   user_inputs dict (signal name -> list of values)
         |
         v
    simulate()        -->   signals dict (signal name -> list of values per step)
         |
         v
    plot_wave()       -->   matplotlib GUI window


---


4. PROJECT FILE STRUCTURE

The project consists of the following files:

    main.py
        The entry point of the program. Handles command-line arguments, calls the parser, runs the interactive input prompt, calls the simulator, prints the signal table to the console, and opens the waveform window.

    parser.py
        Contains all Verilog parsing logic. Strips comments, extracts parameter values, parses port declarations with bus widths, parses assign statements, and parses always blocks including if/else, case/endcase, blocking and non-blocking assignments, and concatenation targets.

    simulator.py
        The simulation engine. Assigns stimulus to inputs, evaluates combinational expressions using Python's eval(), executes always block statements step by step, handles non-blocking assignment semantics, and distributes concatenation results across multiple target signals.

    waveform.py
        The visualization module. Forces an interactive matplotlib backend, then draws each signal as a color-coded stepped trace with value annotations, grid lines, signal name labels, and a legend.

    test.v
        The default Verilog input file. Contains a 4-bit ALU module that demonstrates all four ALU operations: AND, OR, XOR, and addition with carry.

    requirements.txt
        Lists the Python package dependencies. Only matplotlib is required.

    README.md
        A quick-start guide for the project.

    DOCUMENTATION.md
        This file. Full project documentation.


---


5. HOW THE SYSTEM WORKS — PIPELINE DESCRIPTION

Step 1: Reading the Verilog File

When the program starts, main.py resolves the path to the Verilog file. If a file path is given as a command-line argument it is used; otherwise the default test.v in the project folder is loaded. The file is read as a UTF-8 text string.

Step 2: Parsing

The parse_verilog() function in parser.py processes the source text in several passes:

    - All single-line comments (// ...) and block comments (/* ... */) are removed.
    - Parameter declarations are extracted so that bus widths expressed as expressions (for example [width-1:0]) can be evaluated numerically.
    - Input, output, inout, wire, and reg declarations are scanned with regular expressions. For each declaration the bit-width is computed from the MSB and LSB expressions.
    - Continuous assign statements are extracted as (target, expression) pairs.
    - Every always @(...) block is located. The sensitivity list is parsed to identify clock signals and edge types. The block body is then recursively parsed into a tree of statement dictionaries covering if/else, case/endcase, blocking assignments, non-blocking assignments, and concatenation assignments.

The result is a single Python dictionary containing all of this information.

Step 3: Interactive Input Prompt

After parsing, the program prints a summary of the parsed structure and asks the user how many time steps to simulate. It then identifies which input signals are clocks (these are auto-generated as a toggling 0-1-0-1 pattern) and prompts the user to enter values for every remaining input signal. For each signal the prompt shows the bit-width and the valid value range. The user can enter one value per time step separated by spaces, or a single value that will be repeated for all steps. Values are validated and the user is re-prompted if anything is out of range.

Step 4: Simulation

The simulate() function runs a loop from time step 0 to steps-1. At each step:

    - A snapshot called current is built from all signal values known at this step.
    - Combinational assign expressions are evaluated in topological order (so that if one assign depends on another, the dependency is computed first). Results are stored in both current and the signals dictionary.
    - Each always block is processed. If the block is clock-driven (posedge or negedge), it fires only when the clock transitions in the correct direction. If the block is combinational (always @(*)), it fires every step. The block body is executed by walking the statement tree, evaluating expressions, and writing results to a next_state dictionary.
    - After all blocks are processed, next_state is committed as the new register state and appended to the signals dictionary.

At the end of the loop, all signals are padded to the same length if needed.

Step 5: Console Output

Before opening the waveform window, the program prints a formatted table of all signal values across all time steps to the terminal. This allows the user to verify the simulation numerically.

Step 6: Waveform Visualization

The plot_wave() function creates a matplotlib figure. Each signal is drawn as a stepped trace in its own horizontal lane, vertically offset so the traces do not overlap. Each trace is filled with a faint color and annotated with the numeric value at each step. Signal names appear on the left y-axis. A color legend is shown in the top-right corner. The window is displayed in blocking mode so the program waits until the user closes it.


---


6. SUPPORTED VERILOG CONSTRUCTS

The following Verilog constructs are supported by the parser and simulator:

    Supported:
        module and endmodule declarations
        input, output, and inout port declarations (scalar and bus [msb:lsb])
        wire and reg signal declarations (scalar and bus)
        parameter declarations (used to resolve parameterized bus widths)
        assign statements for combinational logic
        always @(*) blocks for combinational always logic
        always @(posedge signal) blocks for rising-edge sequential logic
        always @(negedge signal) blocks for falling-edge sequential logic
        if and else statements inside always blocks
        case and endcase statements inside always blocks (including default)
        Blocking assignments (=) inside always blocks
        Non-blocking assignments (<=) inside always blocks
        Concatenation assignment targets such as {cout, d} = expr
        Verilog numeric literals: binary (4'b1010), hexadecimal (8'hFF), decimal (8'd200)
        Bitwise operators: & (AND), | (OR), ^ (XOR), ~ (NOT)
        Logical operators: && (AND), || (OR), ! (NOT)
        Arithmetic operators: + (addition), - (subtraction), * (multiplication)

    Not supported:
        always blocks with multiple sensitivity list items such as always @(posedge clk, posedge rst)
        Asynchronous reset logic
        assign statements spanning multiple lines
        function and task definitions
        generate blocks
        Module instantiation (sub-modules)
        Multi-dimensional arrays and memories
        X (unknown) and Z (high-impedance) signal states
        Timing delays (#10)


---


7. INSTALLATION AND REQUIREMENTS

Python Version:
    Python 3.8 or later is required.

Dependencies:
    Only one external package is needed: matplotlib version 3.7 or later.

To install dependencies, run the following command in the project folder:

    pip install -r requirements.txt

The requirements.txt file contains:

    matplotlib>=3.7

No other installation steps are needed. All other modules used (re, pathlib, sys) are part of the Python standard library.


---


8. HOW TO RUN THE PROGRAM

To run the program using the default test.v file:

    python main.py

To run the program with a different Verilog file:

    python main.py path/to/your_design.v

After launching, the program will:

    1. Print the parsed structure (inputs, outputs, registers, assigns, always blocks).
    2. Ask how many time steps to simulate.
    3. For each non-clock input, show its bit-width and valid range, then wait for the user to enter values.
    4. Print a table of all simulated signal values.
    5. Open a waveform window.

Input entry rules:

    - Enter one integer per time step, separated by spaces.
      Example for a 4-bit signal over 4 steps:  3 7 12 0

    - Enter a single integer to use the same value for all steps.
      Example:  5   (will be used for every step)

    - If fewer values are entered than the number of steps, the last value is repeated automatically.

    - If more values are entered than the number of steps, only the first N are used.

    - Values must be in the range 0 to (2^width - 1). For example, a 2-bit signal accepts 0, 1, 2, or 3.

    - Clock signals are not prompted. They are automatically generated as a toggling 0-1-0-1 pattern.


---


9. SOURCE CODE DOCUMENTATION


9.1 main.py — Entry Point and User Interface

Purpose:
    main.py is the top-level script that ties all components together. It handles the command-line interface, calls the parser, runs the interactive terminal prompt, calls the simulator, prints results, and opens the waveform window.

Imports:
    sys         — for reading command-line arguments and exiting on error
    pathlib.Path — for resolving file paths in a cross-platform way
    parse_verilog (from parser.py) — the Verilog parsing function
    simulate, _find_clocks (from simulator.py) — the simulation function and clock detector
    plot_wave (from waveform.py) — the waveform plotting function


Function: _prompt_inputs(input_names, clock_names, widths, steps)

    Purpose:
        Interactively collects input signal values from the user in the terminal. It skips clock signals (which are auto-generated) and prompts the user for every other input. It validates that all entered values are integers within the valid range for the signal's bit-width.

    Parameters:
        input_names  — list of all input signal names from the parsed module
        clock_names  — set of signal names identified as clocks (not prompted)
        widths       — dictionary mapping each signal name to its bit-width
        steps        — number of simulation time steps

    Returns:
        A dictionary mapping each non-clock input name to a list of integers, one per time step.

    Behavior details:
        - For a signal of width W, the valid range is 0 to (2^W - 1).
        - A single entered value is repeated for all steps.
        - Too-short lists are padded with the last value.
        - Too-long lists are truncated to the first N values.
        - Invalid input causes a re-prompt with an error message.

    Code:

        def _prompt_inputs(input_names, clock_names, widths, steps):
            user_inputs = {}
            non_clock = [n for n in input_names if n not in clock_names]

            for name in non_clock:
                w      = widths.get(name, 1)
                maxval = (1 << w) - 1
                hint   = f"  {name} [{w}-bit, 0..{maxval}] > "

                while True:
                    raw = input(hint).strip()
                    parts = raw.split()
                    try:
                        vals = [int(p) for p in parts]
                    except ValueError:
                        print(f"    [!] Enter integers only (0..{maxval}). Try again.")
                        continue

                    out_of_range = [v for v in vals if not (0 <= v <= maxval)]
                    if out_of_range:
                        print(f"    [!] Values {out_of_range} are out of range.")
                        continue

                    if len(vals) == 1:
                        vals = vals * steps
                    while len(vals) < steps:
                        vals.append(vals[-1])
                    user_inputs[name] = vals[:steps]
                    break

            return user_inputs


Function: main()

    Purpose:
        The program entry point. Resolves the Verilog file path, reads the file, calls the parser, asks for the number of steps, collects user inputs, runs the simulation, prints the signal table, and opens the waveform window.

    Code:

        def main():
            _here = Path(__file__).resolve().parent

            if len(sys.argv) > 1:
                vfile = Path(sys.argv[1])
                if not vfile.is_absolute():
                    vfile = _here / vfile
            else:
                vfile = _here / "test.v"

            if not vfile.exists():
                print(f"[ERROR] File not found: {vfile}")
                sys.exit(1)

            code   = vfile.read_text(encoding="utf-8")
            parsed = parse_verilog(code)

            while True:
                raw = input("  How many time steps to simulate? [default: 10] > ").strip()
                if raw == "":
                    steps = 10
                    break
                if raw.isdigit() and int(raw) > 0:
                    steps = int(raw)
                    break

            clock_names = _find_clocks(parsed)
            user_inputs = _prompt_inputs(parsed["inputs"], clock_names,
                                         parsed["widths"], steps)

            signals = simulate(parsed, steps=steps, user_inputs=user_inputs)
            plot_wave(signals, title=f"Waveform - {vfile.name}")


---


9.2 parser.py — Verilog Parser

Purpose:
    parser.py converts raw Verilog source text into a structured Python dictionary that the simulator can process. It uses Python's re (regular expressions) module exclusively — there is no external Verilog parsing library. The parser handles comments, parameter declarations, port and signal declarations with bus widths, continuous assign statements, and always blocks with full control flow.

Imports:
    re — Python standard library regular expression module


Function: _eval_width(msb_expr, lsb_expr, params)

    Purpose:
        Computes the integer bit-width of a bus signal from its MSB and LSB expressions. The expressions may contain parameter names (for example "width-1" and "0") which are substituted with their numeric values before evaluation.

    Parameters:
        msb_expr — string expression for the most significant bit index (e.g. "3" or "width-1")
        lsb_expr — string expression for the least significant bit index (e.g. "0")
        params   — dictionary of parameter names to their integer values

    Returns:
        Integer bit-width. Returns 1 if evaluation fails.

    Example:
        _eval_width("width-1", "0", {"width": 4})  -->  4

    Code:

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


Function: parse_verilog(code)

    Purpose:
        The main parser function. Accepts the full Verilog source as a string and returns a structured dictionary describing the module's interface and behavior.

    Parameters:
        code — string containing the full Verilog source text

    Returns:
        A dictionary with the following keys:

            "inputs"        — list of input port names
            "outputs"       — list of output port names
            "inouts"        — list of bidirectional port names
            "wires"         — list of wire signal names
            "regs"          — list of register signal names
            "widths"        — dictionary mapping every signal name to its bit-width
            "assigns"       — list of (target_name, expression_string) tuples
            "always_blocks" — list of parsed always block dictionaries

    Processing steps:

        Step 1 — Strip comments:
            All // single-line comments and /* */ block comments are removed using re.sub().

        Step 2 — Extract parameters:
            All parameter declarations are found with a regular expression and stored in a dictionary. This allows bus widths like [width-1:0] to be resolved numerically.

        Step 3 — Parse declarations:
            The inner function _parse_decls(keyword) scans for all declarations of a given type (input, output, wire, reg, etc.). For each match it extracts the optional [msb:lsb] bus width expression and the comma-separated list of signal names. Combined declarations like "output reg" are normalized before parsing.

        Step 4 — Parse assign statements:
            A regular expression finds all "assign target = expression;" lines and stores them as (target, expression) pairs.

        Step 5 — Parse always blocks:
            The function _parse_always_blocks() is called to find and parse every always @(...) block.

        Step 6 — Build widths dictionary:
            All signal names from all declaration types are merged into a single widths dictionary.

    Code (key section):

        def parse_verilog(code):
            code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
            code = re.sub(r'//[^\n]*', '', code)

            params = {}
            for pm in re.finditer(r'\bparameter\b\s+(\w+)\s*=\s*(\d+)', code):
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

            inputs  = _parse_decls('input',  code_norm)
            outputs = _parse_decls('output', code_norm)
            assigns = [(m.group(1), m.group(2).strip())
                       for m in re.finditer(r'assign\s+(\w+)\s*=\s*(.+?);', code)]
            always_blocks = _parse_always_blocks(code)

            return {
                "inputs": [n for n, _ in inputs],
                "outputs": [n for n, _ in outputs],
                "widths": widths,
                "assigns": assigns,
                "always_blocks": always_blocks,
                ...
            }


Function: _parse_always_blocks(code)

    Purpose:
        Finds every always @(...) block in the source text, parses the sensitivity list to identify clock signals and edge types, extracts the block body, and recursively parses the body into a list of statement dictionaries.

    Returns:
        A list of dictionaries, one per always block, each with keys:
            "sensitivity" — the raw sensitivity string (e.g. "posedge clk" or "*")
            "clock"       — the clock signal name, or None for combinational blocks
            "edge"        — "posedge", "negedge", or None
            "body"        — list of parsed statement dictionaries


Function: _extract_block(code, start)

    Purpose:
        Starting at position start in the code string, extracts either a begin...end block (returning its inner content) or a single statement ending at a semicolon. Handles nested begin...end by tracking depth.

    Returns:
        A tuple of (block_text, end_index).

    Code:

        def _extract_block(code, start):
            i = start
            while i < len(code) and code[i] in ' \t\n\r':
                i += 1

            if i < len(code) and code[i:i+5] == 'begin':
                depth = 1
                j = i + 5
                while j < len(code) and depth > 0:
                    if code[j:j+5] == 'begin':
                        depth += 1; j += 5
                    elif code[j:j+3] == 'end':
                        depth -= 1; j += 3
                    else:
                        j += 1
                return code[i+5:j-3].strip(), j
            else:
                end = code.find(';', i)
                return code[i:end+1].strip(), end + 1


Function: _parse_statements(text)

    Purpose:
        Recursively parses a block of Verilog statements into a list of statement dictionaries. Handles if/else, case/endcase, blocking assignments (=), non-blocking assignments (<=), and concatenation assignment targets ({a, b} = expr).

    Statement dictionary formats:

        Blocking assignment:
            { "type": "blocking", "target": "d", "expr": "a & b" }

        Non-blocking assignment:
            { "type": "nonblocking", "target": "Q", "expr": "D" }

        Concatenation assignment:
            { "type": "blocking", "target": ["cout", "d"],
              "expr": "a + b + cin", "concat": True }

        If statement:
            { "type": "if", "condition": "rst",
              "true_branch": [...], "false_branch": [...] }

        Case statement:
            { "type": "case", "selector": "control",
              "items": [
                  { "value": "2'b00", "stmts": [...] },
                  { "value": "default", "stmts": [...] }
              ]}


Function: _parse_case_items(body)

    Purpose:
        Parses the body of a case block into a list of items. Each item has a label value and a list of statements. Supports both single-statement items and begin...end block items.


---


9.3 simulator.py — Simulation Engine

Purpose:
    simulator.py drives the discrete-time simulation. It assigns stimulus values to input signals, evaluates combinational logic expressions, executes always block statement trees, handles non-blocking assignment semantics, and distributes concatenation results across multiple target signals. The result is a complete time-history of every signal in the module.

Imports:
    re — Python standard library regular expression module


Constant: _STIMULUS_ROWS

    Purpose:
        Default input patterns used when the user does not provide values for an input signal. There are four rows of eight values each. Input signals are assigned rows by index (input 0 gets row 0, input 1 gets row 1, etc., cycling if there are more than four inputs).

    Value:

        _STIMULUS_ROWS = [
            [0, 1, 1, 0, 1, 0, 1, 1],
            [1, 1, 0, 0, 1, 1, 0, 0],
            [0, 1, 0, 1, 0, 1, 0, 1],
            [1, 0, 1, 0, 1, 0, 1, 0],
        ]


Function: _clock_signal(steps)

    Purpose:
        Generates an automatic clock signal that toggles between 0 and 1 every step, simulating a clock with a period of 2 time steps.

    Code:

        def _clock_signal(steps):
            return [i % 2 for i in range(steps)]


Function: _normalize_expr(expr)

    Purpose:
        Converts a Verilog expression string into a valid Python expression string by replacing Verilog-specific operators and numeric literals with their Python equivalents.

    Operator mapping:

        Verilog &&   -->  Python and
        Verilog ||   -->  Python or
        Verilog !    -->  Python not
        Verilog ~    -->  Python ~ (bitwise NOT)
        Verilog &    -->  Python & (bitwise AND)
        Verilog |    -->  Python | (bitwise OR)
        Verilog ^    -->  Python ^ (bitwise XOR)
        4'b1010      -->  10  (binary literal converted to integer)
        8'hFF        -->  255 (hexadecimal literal converted to integer)
        8'd200       -->  200 (decimal literal kept as integer)

    Code:

        def _normalize_expr(expr):
            expr = re.sub(r'&&', ' and ', expr)
            expr = re.sub(r'\|\|', ' or ', expr)
            expr = re.sub(r'!(?!=)', ' not ', expr)
            expr = re.sub(r"\d+'b([01]+)", lambda m: str(int(m.group(1), 2)), expr)
            expr = re.sub(r"\d+'h([0-9a-fA-F]+)", lambda m: str(int(m.group(1), 16)), expr)
            expr = re.sub(r"\d+'d(\d+)", lambda m: m.group(1), expr)
            return expr


Function: eval_expr(expr, values)

    Purpose:
        Evaluates a Verilog expression string for one time step given the current signal values. First normalizes the expression, then substitutes all signal names with their current integer values, then calls Python's built-in eval() to compute the result.

    Parameters:
        expr   — Verilog expression string (e.g. "a & b", "a + b + cin")
        values — dictionary mapping signal names to their current integer values

    Returns:
        Integer result of the expression. May be multi-bit for arithmetic expressions.

    Important detail:
        Signal names are substituted in order from longest to shortest. This prevents a signal named "cout" from being partially replaced when another signal named "c" is also present.

    Code:

        def eval_expr(expr, values):
            expr = _normalize_expr(expr)
            for var in sorted(values.keys(), key=len, reverse=True):
                expr = re.sub(rf'\b{re.escape(var)}\b', str(int(values[var])), expr)
            try:
                return int(eval(expr))
            except Exception:
                return 0


Function: _distribute_concat(targets, value, widths, current, next_state, blocking)

    Purpose:
        Handles the Verilog concatenation assignment {cout, d} = expr. The integer result of the expression is split into bit slices and each slice is assigned to the corresponding target signal according to its declared bit-width.

    How it works:
        The targets list is ordered MSB-first (as written in the Verilog). The function iterates the list in reverse (LSB-first) and extracts bit slices from the integer value using bit masking and shifting. For example:

            {cout[1-bit], d[4-bit]} = 23
            23 in binary = 1_0111
            d    = lower 4 bits = 0111 = 7
            cout = upper 1 bit  = 1

    Code:

        def _distribute_concat(targets, value, widths, current, next_state, blocking):
            sig_widths = [widths.get(t, 1) for t in targets]
            total      = sum(sig_widths)
            value      = value & ((1 << total) - 1)

            bit_pos = 0
            for sig, w in zip(reversed(targets), reversed(sig_widths)):
                mask = (1 << w) - 1
                part = (value >> bit_pos) & mask
                bit_pos += w
                if blocking:
                    current[sig]    = part
                    next_state[sig] = part
                else:
                    next_state[sig] = part


Function: _topo_sort_assigns(assigns)

    Purpose:
        Sorts a list of (target, expression) assign pairs so that each expression is evaluated only after all of its dependencies have been computed. This is necessary when one assign output is used as an input to another assign.

    Algorithm:
        Iterative dependency resolution. In each pass, any assign whose expression depends only on already-resolved signals is moved to the output order. The process repeats until all assigns are ordered or no further progress can be made (indicating a cycle, in which case remaining assigns are appended in their original order).

    Example:
        Given:  assign C = B;   assign B = A;
        Without sorting, C would be evaluated before B is updated.
        After sorting:  assign B = A;   assign C = B;

    Code:

        def _topo_sort_assigns(assigns):
            output_names = {a[0] for a in assigns}
            order, remaining, resolved = [], list(assigns), set()

            for _ in range(len(assigns) + 1):
                still_remaining = []
                for out, expr in remaining:
                    deps = set(re.findall(r'\b([A-Za-z_]\w*)\b', expr))
                    if not (deps & output_names) - resolved:
                        order.append((out, expr))
                        resolved.add(out)
                    else:
                        still_remaining.append((out, expr))
                remaining = still_remaining
                if not remaining:
                    break

            return order + remaining


Function: _exec_statements(stmts, current, next_state, widths)

    Purpose:
        Walks a list of parsed statement dictionaries and executes each one. This is the core interpreter for always block bodies. It handles all statement types produced by the parser.

    Parameters:
        stmts      — list of statement dictionaries from the parser
        current    — dictionary of signal values visible at the start of this clock edge
        next_state — dictionary accumulating the results of non-blocking assignments
        widths     — signal bit-width dictionary (used for concatenation splitting)

    Execution rules by statement type:

        blocking assignment:
            Evaluates the expression using current values, writes the result to both current (immediately visible to later statements in the same block) and next_state.

        nonblocking assignment:
            Evaluates the expression using current values, writes only to next_state. The result is not visible to other statements in the same block (this matches real Verilog non-blocking semantics).

        concat assignment:
            Evaluates the expression, then calls _distribute_concat() to split the result across multiple target signals.

        if statement:
            Evaluates the condition expression. If true, recursively executes the true_branch statements. Otherwise recursively executes the false_branch statements.

        case statement:
            Evaluates the selector expression. Iterates through the case items, evaluating each item's value expression. Executes the matching item's statements. If no item matches, executes the default item if present.

    Code:

        def _exec_statements(stmts, current, next_state, widths=None):
            if widths is None:
                widths = {}
            for stmt in stmts:
                t = stmt["type"]

                if t in ("nonblocking", "blocking"):
                    val = eval_expr(stmt["expr"], current)
                    if stmt.get("concat"):
                        _distribute_concat(stmt["target"], val, widths,
                                           current, next_state, blocking=(t == "blocking"))
                    elif t == "nonblocking":
                        next_state[stmt["target"]] = val
                    else:
                        current[stmt["target"]]    = val
                        next_state[stmt["target"]] = val

                elif t == "if":
                    cond   = eval_expr(stmt["condition"], current)
                    branch = stmt["true_branch"] if cond else stmt["false_branch"]
                    _exec_statements(branch, current, next_state, widths)

                elif t == "case":
                    sel_val = eval_expr(stmt["selector"], current)
                    matched = False
                    for item in stmt["items"]:
                        if item["value"] == "default":
                            continue
                        if sel_val == eval_expr(item["value"], current):
                            _exec_statements(item["stmts"], current, next_state, widths)
                            matched = True
                            break
                    if not matched:
                        for item in stmt["items"]:
                            if item["value"] == "default":
                                _exec_statements(item["stmts"], current, next_state, widths)
                                break


Function: simulate(parsed, steps=10, user_inputs=None)

    Purpose:
        The main simulation function. Runs the full discrete-time simulation loop and returns the complete signal history.

    Parameters:
        parsed      — the dictionary returned by parse_verilog()
        steps       — number of time steps to simulate (default: 10)
        user_inputs — optional dictionary mapping input signal names to lists of values.
                      If provided, these values are used instead of the default patterns.
                      If None, default stimulus patterns are used.

    Returns:
        A dictionary mapping every signal name (inputs, outputs, registers) to a list of integer values, one per time step.

    Per-step logic:

        For each time step t from 0 to steps-1:

            1. Build a snapshot dictionary called current from all signal values at step t.
               Add the current register state to current.

            2. Evaluate all combinational assign expressions in topological order.
               Each result is stored in current (for use by later assigns in the same step)
               and appended to the signals dictionary.

            3. Create next_state as a copy of the current register state.
               This is where non-blocking assignments will write their results.

            4. For each always block:
               - If the block has a clock (posedge/negedge): check whether the clock
                 transitioned in the correct direction between step t-1 and step t.
                 If yes, call _exec_statements() on the block body.
               - If the block is combinational (always @(*)): call _exec_statements()
                 every step.

            5. Set reg_state = next_state (commit non-blocking assignments).
               Append each register's new value to the signals dictionary.

        After the loop, pad any signals that are shorter than steps by repeating their last value.

    Code:

        def simulate(parsed, steps=10, user_inputs=None):
            signals      = {}
            clock_names  = _find_clocks(parsed)
            non_clock_idx = 0

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

            reg_state      = {name: 0 for name in parsed.get("regs", [])}
            sorted_assigns = _topo_sort_assigns(parsed.get("assigns", []))

            for t in range(steps):
                current = {k: signals[k][t] for k in signals if len(signals[k]) > t}
                current.update(reg_state)

                for out, expr in sorted_assigns:
                    val = eval_expr(expr, current)
                    current[out] = val
                    signals.setdefault(out, []).append(val)

                next_state = dict(reg_state)
                for block in parsed.get("always_blocks", []):
                    clk  = block.get("clock")
                    edge = block.get("edge")
                    if clk:
                        clk_now  = current.get(clk, 0)
                        clk_prev = signals.get(clk, [0])[t - 1] if t > 0 else 0
                        rising   = (clk_prev == 0 and clk_now == 1)
                        falling  = (clk_prev == 1 and clk_now == 0)
                        if (edge == "posedge" and rising) or (edge == "negedge" and falling):
                            _exec_statements(block["body"], dict(current),
                                             next_state, parsed.get("widths", {}))
                    else:
                        _exec_statements(block["body"], dict(current),
                                         next_state, parsed.get("widths", {}))

                reg_state = next_state
                for name, val in reg_state.items():
                    signals.setdefault(name, []).append(val)

            for name in signals:
                while len(signals[name]) < steps:
                    signals[name].append(signals[name][-1] if signals[name] else 0)

            return signals


Function: _find_clocks(parsed)

    Purpose:
        Scans the always_blocks list in the parsed dictionary and returns a set of all signal names that are used as clock signals (i.e. appear after posedge or negedge in a sensitivity list).

    Code:

        def _find_clocks(parsed):
            clocks = set()
            for block in parsed.get("always_blocks", []):
                if block.get("clock"):
                    clocks.add(block["clock"])
            return clocks


---


9.4 waveform.py — Waveform Visualizer

Purpose:
    waveform.py is responsible for rendering the simulation results as a digital timing waveform. It uses the matplotlib library to draw each signal as a stepped trace in its own horizontal lane, with color coding, value annotations, grid lines, and a legend.

Imports:
    matplotlib        — for backend selection before pyplot is imported
    matplotlib.pyplot — the main plotting interface
    matplotlib.patches — for creating colored legend patches


Backend Selection

    Before importing matplotlib.pyplot, the module attempts to set an interactive GUI backend. This is necessary because many environments (including some IDEs and terminal configurations) default to the Agg backend, which is non-interactive and causes plt.show() to do nothing visible.

    The module tries backends in this order: TkAgg (uses Python's built-in Tkinter), Qt5Agg, QtAgg. The first one that succeeds is used.

    Code:

        import matplotlib

        for _backend in ("TkAgg", "Qt5Agg", "QtAgg"):
            try:
                matplotlib.use(_backend, force=True)
                break
            except Exception:
                continue

        import matplotlib.pyplot as plt


Constants

    _COLOURS:
        A list of eight hex color codes used to color-code the signal traces. The list cycles if there are more signals than colors.

        _COLOURS = [
            "#2196F3",  # blue
            "#4CAF50",  # green
            "#F44336",  # red
            "#FF9800",  # orange
            "#9C27B0",  # purple
            "#00BCD4",  # cyan
            "#FFEB3B",  # yellow
            "#795548",  # brown
        ]

    _TRACE_HEIGHT = 0.8:
        The height of each trace within its 2-unit row. A value of 0.8 means the trace occupies 80% of the row height, leaving visual spacing between lanes.

    _ROW_SPACING = 2.0:
        The vertical distance in plot units between the baselines of adjacent signal lanes.


Function: plot_wave(signals, title="Digital Waveform")

    Purpose:
        Renders all signals as a digital timing diagram in a matplotlib window.

    Parameters:
        signals — dictionary mapping signal names to lists of integer values (output of simulate())
        title   — string to display as the window and chart title

    Rendering steps:

        1. Determine the number of signals (n) and the number of time steps.

        2. Create a figure sized proportionally: width scales with the number of steps, height scales with the number of signals.

        3. For each signal, in the order they appear in the dictionary:
            a. Compute the vertical baseline as i * _ROW_SPACING where i is the signal index.
            b. Scale the signal values: scaled_value = baseline + value * _TRACE_HEIGHT.
               This maps 0 to the baseline and 1 (or any positive value) to baseline + 0.8.
            c. Draw the trace using ax.step() with where='post', which produces the
               characteristic hold-time shape of a digital waveform.
            d. Add a faint filled area under the trace using ax.fill_between() for visual clarity.
            e. Annotate each time step cell with the numeric value of the signal at that step.
            f. Record the signal name for the y-axis label and the color for the legend.

        4. Set y-axis tick positions and labels to show signal names on the left.

        5. Draw vertical grid lines at each time step boundary.

        6. Draw horizontal separator lines between signal lanes.

        7. Add a color legend in the top-right corner.

        8. Remove the top and right axis spines for a cleaner look.

        9. Call plt.tight_layout() to prevent label clipping, then plt.show(block=True)
           to display the window and wait for the user to close it.

    Code:

        def plot_wave(signals, title="Digital Waveform"):
            names = list(signals.keys())
            n     = len(names)
            steps = max(len(v) for v in signals.values())

            fig, ax = plt.subplots(figsize=(max(10, steps * 0.9), max(3, n * 1.2 + 1.5)))

            patches          = []
            ytick_positions  = []
            ytick_labels     = []

            for i, name in enumerate(names):
                values = signals[name]
                colour = _COLOURS[i % len(_COLOURS)]
                base   = i * _ROW_SPACING

                if len(values) < steps:
                    values = values + [values[-1]] * (steps - len(values))

                scaled = [base + v * _TRACE_HEIGHT for v in values]
                xs     = list(range(steps)) + [steps]
                ys     = scaled + [scaled[-1]]

                ax.step(xs, ys, where='post', color=colour, linewidth=1.8)
                ax.fill_between(xs, base, ys, step='post', color=colour, alpha=0.12)

                for t in range(steps):
                    ax.text(t + 0.5, base + _TRACE_HEIGHT * 0.5,
                            str(values[t]), ha='center', va='center',
                            fontsize=7, color=colour, alpha=0.7)

                ytick_positions.append(base + _TRACE_HEIGHT * 0.5)
                ytick_labels.append(name)
                patches.append(mpatches.Patch(color=colour, label=name))

            ax.set_yticks(ytick_positions)
            ax.set_yticklabels(ytick_labels, fontsize=9)
            ax.set_xlim(0, steps)
            ax.set_ylim(-0.5, n * _ROW_SPACING)
            ax.set_xlabel("Time step", fontsize=10)
            ax.set_title(title, fontsize=12, fontweight='bold')

            for t in range(steps + 1):
                ax.axvline(t, color='#cccccc', linewidth=0.5, zorder=0)
            for i in range(n + 1):
                ax.axhline(i * _ROW_SPACING - 0.3, color='#eeeeee', linewidth=0.8, zorder=0)

            ax.legend(handles=patches, loc='upper right', fontsize=8, framealpha=0.7)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            plt.tight_layout()
            plt.show(block=True)


---


9.5 test.v — Sample Verilog Design (4-bit ALU)

Purpose:
    test.v is the default Verilog input file provided with the project. It implements a 4-bit Arithmetic Logic Unit (ALU) that performs four operations selected by a 2-bit control signal. It demonstrates all major features supported by the parser and simulator: multi-bit bus signals, a combinational always @(*) block, a case statement, blocking assignments, and a concatenation assignment for the carry-out bit.

Full source code:

    // n-bit ALU  (width = 4 for simulation)
    // Inputs : a[3:0], b[3:0], cin, control[1:0]
    // Outputs: d[3:0], cout

    module ALU (a, b, cin, control, d, cout);
      input  [3:0] a;
      input  [3:0] b;
      input        cin;
      input  [1:0] control;
      output [3:0] d;
      output       cout;

      reg [3:0] d;
      reg       cout;

      always @(*) begin
        case (control)
          2'b00 : begin d = a & b;             cout = 0; end
          2'b01 : begin d = a | b;             cout = 0; end
          2'b10 : begin d = a ^ b;             cout = 0; end
          2'b11 : begin {cout, d} = a + b + cin;         end
          default: begin d = 0;                cout = 0; end
        endcase
      end

    endmodule

ALU operation table:

    control value | Binary | Operation       | Output
    0             | 2'b00  | Bitwise AND     | d = a AND b,  cout = 0
    1             | 2'b01  | Bitwise OR      | d = a OR b,   cout = 0
    2             | 2'b10  | Bitwise XOR     | d = a XOR b,  cout = 0
    3             | 2'b11  | Addition        | {cout, d} = a + b + cin

Signal widths:

    Signal   | Direction | Width  | Description
    a        | input     | 4 bits | First operand
    b        | input     | 4 bits | Second operand
    cin      | input     | 1 bit  | Carry input (used only for addition)
    control  | input     | 2 bits | Operation selector (0=AND, 1=OR, 2=XOR, 3=ADD)
    d        | output    | 4 bits | Result
    cout     | output    | 1 bit  | Carry output (set only during addition)


---


10. INTERNAL DATA STRUCTURES

This section shows the exact shape of the two main data structures used throughout the program.


The parsed dictionary (output of parse_verilog):

    {
        "inputs":  ["a", "b", "cin", "control"],
        "outputs": ["d", "cout"],
        "inouts":  [],
        "wires":   [],
        "regs":    ["d", "cout"],
        "widths":  {
            "a":       4,
            "b":       4,
            "cin":     1,
            "control": 2,
            "d":       4,
            "cout":    1
        },
        "assigns": [],
        "always_blocks": [
            {
                "sensitivity": "*",
                "clock": None,
                "edge":  None,
                "body": [
                    {
                        "type": "case",
                        "selector": "control",
                        "items": [
                            {
                                "value": "2'b00",
                                "stmts": [
                                    { "type": "blocking", "target": "d",    "expr": "a & b" },
                                    { "type": "blocking", "target": "cout", "expr": "0"     }
                                ]
                            },
                            {
                                "value": "2'b11",
                                "stmts": [
                                    { "type": "blocking", "target": ["cout", "d"],
                                      "expr": "a + b + cin", "concat": True }
                                ]
                            },
                            {
                                "value": "default",
                                "stmts": [
                                    { "type": "blocking", "target": "d",    "expr": "0" },
                                    { "type": "blocking", "target": "cout", "expr": "0" }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }


The signals dictionary (output of simulate):

    {
        "a":       [12, 12, 12, 12],
        "b":       [10, 10, 10, 10],
        "cin":     [0,  0,  0,  1 ],
        "control": [0,  1,  2,  3 ],
        "d":       [8,  14, 6,  7 ],
        "cout":    [0,  0,  0,  1 ]
    }

Each key is a signal name. Each value is a list of integers with one entry per simulated time step. The index in the list corresponds directly to the time step number.


---


11. EXAMPLE SIMULATION SESSION

The following is a complete example of running the program with the default ALU test file, simulating 4 time steps and entering values that test all four ALU operations.

Command:

    python main.py

Terminal output:

    [INFO]  Loading: test.v

    --- Parsed structure -------------------------------------------
      Inputs  : ['a', 'b', 'cin', 'control']
      Outputs : ['d', 'cout']
      Regs    : ['d', 'cout']
      Wires   : []
      Assigns : []
      Always  : 1 block(s)

      How many time steps to simulate? [default: 10] > 4

    ============================================================
      INPUT CONFIGURATION
    ============================================================
      Simulation steps : 4
      Clock signals    : none

      For each input enter space-separated integer values,
      one per time step (or a single value repeated for all steps).
    ------------------------------------------------------------
      a        [4-bit, 0..15] > 12 12 12 12
      b        [4-bit, 0..15] > 10 10 10 10
      cin      [1-bit, 0..1]  > 0 0 0 1
      control  [2-bit, 0..3]  > 0 1 2 3
    ============================================================

    --- Simulated signals ------------------------------------------
               t0    t1    t2    t3
      a        12    12    12    12
      b        10    10    10    10
      cin      0     0     0     1
      control  0     1     2     3
      d        8     14    6     7
      cout     0     0     0     1

    [INFO]  Opening waveform window ...

Verification of results:

    t0: control=0 (AND),  a=12 (1100), b=10 (1010)  -->  d = 1100 & 1010 = 1000 = 8,  cout = 0   CORRECT
    t1: control=1 (OR),   a=12 (1100), b=10 (1010)  -->  d = 1100 | 1010 = 1110 = 14, cout = 0   CORRECT
    t2: control=2 (XOR),  a=12 (1100), b=10 (1010)  -->  d = 1100 ^ 1010 = 0110 = 6,  cout = 0   CORRECT
    t3: control=3 (ADD),  a=12, b=10, cin=1          -->  12 + 10 + 1 = 23 = 1_0111
                                                          d = 0111 = 7, cout = 1                   CORRECT


---


12. SCREENSHOTS

Waveform Window — ALU Simulation (AND, OR, XOR, Addition)

    [Image to be added]


Waveform Window — D Flip-Flop with Synchronous Reset

    [Image to be added]


Waveform Window — Combinational Logic (Multiple assign statements)

    [Image to be added]


Terminal — Interactive Input Session

    [Image to be added]


Terminal — Simulated Signal Table Output

    [Image to be added]


---


13. KNOWN LIMITATIONS

The following limitations exist in the current version of the tool:

    1. No asynchronous reset support.
       The sensitivity list parser only reads the first item. A block written as
       always @(posedge clk, posedge rst) will only detect the clock and will not
       model the asynchronous reset behavior.

    2. Single-line assign statements only.
       The assign parser uses a single-line regular expression. An assign statement
       that spans multiple lines will not be parsed correctly.

    3. No function or task support.
       Verilog function and task definitions are not parsed or executed.

    4. No generate blocks.
       Parameterized structural instantiation using generate/endgenerate is not supported.

    5. Single module only.
       Only the first module...endmodule block in the file is simulated. Sub-module
       instantiation is not supported.

    6. No X or Z states.
       All undriven or uninitialized signals default to 0. High-impedance (Z) and
       unknown (X) states are not modeled.

    7. Use of eval() for expression evaluation.
       Python's built-in eval() is used to evaluate expressions. This is acceptable
       for trusted local Verilog files but would be a security risk if used with
       untrusted input.

    8. Combinational loop detection.
       If two assign statements depend on each other (a combinational loop), the
       topological sort falls back to the original order without issuing a warning.


---


14. FUTURE IMPROVEMENTS

The following enhancements are planned or suggested for future versions:

    1. Asynchronous reset support.
       Parse multiple sensitivity list items and model async reset behavior correctly.

    2. Multi-module support.
       Parse module instantiation statements and simulate hierarchical designs.

    3. Stimulus file input.
       Allow the user to load input values from a CSV or JSON file instead of
       entering them manually in the terminal.

    4. Waveform export.
       Add an option to save the waveform plot as a PNG or SVG image, or export
       the signal data as a VCD (Value Change Dump) file compatible with GTKWave.

    5. GUI file browser.
       Replace the command-line file path argument with a graphical file picker dialog.

    6. Web interface.
       Replace the terminal prompt with a browser-based interface where the user
       can paste Verilog code and enter stimulus values in a form.

    7. X and Z state modeling.
       Represent unknown (X) and high-impedance (Z) signal states.

    8. Better error reporting.
       Show line numbers and descriptive error messages when unsupported or
       malformed Verilog constructs are encountered.

    9. function and task support.
       Parse and execute Verilog function and task definitions.


---


15. CONCLUSION

This project successfully demonstrates how a simplified Verilog parser and simulator can be built using only Python's standard library and the matplotlib package. The tool covers the essential workflow of a hardware simulator: reading a hardware description, parsing it into an internal representation, simulating its behavior over time, and visualizing the results.

The four-module architecture (parser, simulator, waveform, main) provides a clean separation of concerns. Each module has a single well-defined responsibility, making the code readable, maintainable, and easy to extend.

The interactive terminal prompt for input stimulus makes the tool practical to use without requiring the user to modify any Python code. The waveform window provides immediate visual feedback that helps in understanding the behavior of the simulated circuit.

While the tool does not aim to replace professional EDA software, it serves as a strong educational and portfolio project that demonstrates understanding of digital logic, hardware description languages, parsing techniques, simulation algorithms, and data visualization.
