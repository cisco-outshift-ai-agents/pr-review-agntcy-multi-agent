def wrap_prompt(*args):
    lines = []
    min_indent = 999999  # arbitrary large number

    for arg in args:
        for line in arg.split("\n"):
            if line.lstrip():
                indent = len(line) - len(line.lstrip())
                min_indent = min(min_indent, indent)
            lines.append(line)

    normalized_lines = []
    for line in lines:
        if line.lstrip():
            current_indent = len(line) - len(line.lstrip())
            relative_indent = current_indent - min_indent
            normalized_lines.append(" " * relative_indent + line.lstrip().rstrip())
        else:
            normalized_lines.append("")

    return "\n".join(normalized_lines)
