def wrap_prompt(*args):
    lines = []
    for arg in args:
        for line in arg.split("\n"):
            # trim leading and trailing whitespace
            line = line.strip()
            lines.append(line)
    return "\n".join(lines)
