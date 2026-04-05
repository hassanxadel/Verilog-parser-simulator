import re

def parse_verilog(code):

    code = re.sub(r'//.*', '', code)

    # Extract inputs, outputs, assigns
    inputs = re.findall(r'input\s+(.+?);', code)
    outputs = re.findall(r'output\s+(.+?);', code)
    assigns = re.findall(r'assign\s+(\w+)\s*=\s*(.+?);', code)

    def split_vars(lst):
        return [v.strip() for group in lst for v in group.split(',')]

    parsed = {
        "inputs": split_vars(inputs),
        "outputs": split_vars(outputs),
        "assigns": assigns
    }

    return parsed
