# Read the largest force from a list of OUTCAR lines.
# Uses the last TOTAL-FORCE block. Return None if no block is found.
def max_force_from_lines(lines):
    max_force = None
    reading = False
    dash_count = 0
    block_max = 0.0

    for line in lines:
        if config.FORCE_BLOCK_TEXT in line:
            reading = True
            dash_count = 0
            block_max = 0.0
            continue

        if not reading:
            continue

        # The block sits between two lines of dashes
        if line.strip().startswith("---"):
            dash_count = dash_count + 1
            if dash_count == 2:
                reading = False
                max_force = block_max
            continue

        words = line.split()
        if len(words) < 6:
            continue

        try:
            fx = float(words[3])
            fy = float(words[4])
            fz = float(words[5])
        except ValueError:
            continue

        size = (fx * fx + fy * fy + fz * fz) ** 0.5
        if size > block_max:
            block_max = size

    return max_force


# Return the largest force on any atom in the last force block of OUTCAR.
# Return None if no complete block is found.
def get_max_force(outcar_path):
    text = read_tail(outcar_path, config.TAIL_BYTES)
    force = max_force_from_lines(text.splitlines())
    if force is not None:
        return force

    if not os.path.isfile(outcar_path):
        return None

    # Not in the tail: read the whole file line by line
    with open(outcar_path, "r", errors="replace") as f:
        return max_force_from_lines(f)


# Return the absolute energy change between the last two ionic steps.
# Uses the F= values in OSZICAR. Return None if fewer than two steps.
def get_last_ionic_energy_change(oszicar_path):
    energies = []

    for line in read_lines(oszicar_path):
        if "F=" not in line:
            continue
        after = line.split("F=")[1].split()
        if len(after) == 0:
            continue
        try:
            energies.append(float(after[0]))
        except ValueError:
            continue

    if len(energies) < 2:
        return None

    return abs(energies[-1] - energies[-2])