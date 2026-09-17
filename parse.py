# parse.py
# Small functions that read VASP and SLURM files.
# Each function reads one thing and returns a simple value.
# No function here decides the job status. classify.py does that.

import os
import sys

import config


# Read the last nbytes of a file and return it as text.
# Return an empty string if the file does not exist.
def read_tail(file_path, nbytes):
    if not os.path.isfile(file_path):
        return ""

    size = os.path.getsize(file_path)
    start = size - nbytes
    if start < 0:
        start = 0

    # Open in binary mode so seek works on any file size.
    with open(file_path, "rb") as f:
        f.seek(start)
        data = f.read()

    # Replace any broken characters instead of stopping with an error.
    return data.decode("utf-8", errors="replace")


# Read all lines of a small text file.
# Return an empty list if the file does not exist.
def read_lines(file_path):
    if not os.path.isfile(file_path):
        return []

    with open(file_path, "r", errors="replace") as f:
        lines = f.readlines()

    return lines


# Return the value of one INCAR tag as text, for example "1E-6".
# Return None if the tag is not set.
def get_incar_value(calc_dir, key):
    incar_path = os.path.join(calc_dir, config.INCAR_NAME)
    lines = read_lines(incar_path)
    key = key.upper()

    for line in lines:
        # Remove comments that start with # or !
        line = line.split("#")[0]
        line = line.split("!")[0]

        # One line can hold several tags separated by ;
        parts = line.split(";")

        for part in parts:
            if "=" not in part:
                continue

            name, value = part.split("=", 1)
            name = name.strip().upper()
            value = value.strip()

            if name == key:
                return value

    return None


# Return two text values from KPOINTS: scheme and mesh.
# Example: ("Gamma", "6 6 6")
def get_kpoints_info(calc_dir):
    kpoints_path = os.path.join(calc_dir, config.KPOINTS_NAME)
    lines = read_lines(kpoints_path)

    if len(lines) < 4:
        return "not found", ""

    count = lines[1].strip()
    scheme_line = lines[2].strip()
    mesh = " ".join(lines[3].split()[:3])

    # A count other than 0 means an explicit list of k points.
    if count != "0":
        return "explicit list", ""

    first_letter = scheme_line[:1].upper()

    if first_letter == "G":
        return "Gamma", mesh
    if first_letter == "M":
        return "Monkhorst Pack", mesh
    if first_letter == "A":
        return "Auto length", mesh

    return "unknown", mesh


# Find the slurm file with the highest job ID in a directory.
# Return (full path, job ID as text), or (None, None) if none exist.
def find_latest_slurm(calc_dir):
    best_path = None
    best_id = None

    for name in os.listdir(calc_dir):
        if not name.startswith(config.SLURM_PREFIX):
            continue
        if not name.endswith(config.SLURM_SUFFIX):
            continue

        # Take the part between the prefix and the suffix.
        start = len(config.SLURM_PREFIX)
        end = len(name) - len(config.SLURM_SUFFIX)
        job_id = name[start:end]

        # Skip names like slurm-test.out
        if not job_id.isdigit():
            continue

        if best_id is None or int(job_id) > int(best_id):
            best_id = job_id
            best_path = os.path.join(calc_dir, name)

    return best_path, best_id


# Return True if OUTCAR ends with the VASP timing block.
def has_normal_end(outcar_path):
    text = read_tail(outcar_path, config.TAIL_BYTES)
    return config.NORMAL_END_TEXT in text


# Return True if an ionic relaxation met EDIFFG.
# Always False for static runs, since VASP does not print this line.
def is_relax_done(outcar_path):
    text = read_tail(outcar_path, config.TAIL_BYTES)
    return config.RELAX_DONE_TEXT in text


# Return True if a line from OSZICAR is one electronic step.
def is_scf_line(line):
    stripped = line.strip()
    for start in config.SCF_LINE_STARTS:
        if stripped.startswith(start):
            return True
    return False


# Count electronic steps in the last ionic step of OSZICAR.
# Return 0 if OSZICAR is missing or has no electronic steps.
def count_last_scf_steps(oszicar_path):
    lines = read_lines(oszicar_path)

    count = 0
    last_finished_count = 0

    for line in lines:
        if is_scf_line(line):
            count = count + 1
        elif "F=" in line:
            # A line with F= closes one ionic step.
            last_finished_count = count
            count = 0

    # If the file ends inside an ionic step, report that step.
    if count > 0:
        return count

    return last_finished_count


# Take one OUTCAR line and return the energy(sigma->0) value.
# Return None if the value cannot be read.
def energy_from_line(line):
    after = line.split(config.ENERGY_TEXT)[1]
    after = after.replace("=", " ")
    words = after.split()

    if len(words) == 0:
        return None

    try:
        return float(words[0])
    except ValueError:
        return None


# Return the last energy(sigma->0) in OUTCAR as a number in eV.
# Return None if not found.
def get_final_energy(outcar_path):
    # First try the tail, which is fast.
    text = read_tail(outcar_path, config.TAIL_BYTES)
    energy = None

    for line in text.splitlines():
        if config.ENERGY_TEXT in line:
            energy = energy_from_line(line)

    if energy is not None:
        return energy

    # Not in the tail: read the whole file line by line.
    if not os.path.isfile(outcar_path):
        return None

    with open(outcar_path, "r", errors="replace") as f:
        for line in f:
            if config.ENERGY_TEXT in line:
                energy = energy_from_line(line)

    return energy


# Search a slurm file for known error text.
# Return the label of the first pattern found, or None.
def find_error(slurm_path):
    if slurm_path is None:
        return None

    text = read_tail(slurm_path, config.TAIL_BYTES)

    for pattern, label in config.ERROR_PATTERNS:
        if pattern in text:
            return label

    return None

# Search one file for known error text.
# A pattern is text, or a list of texts that must all be on one line.
# Return (label, matching line), or (None, None) if nothing is found.
def find_error_details(file_path):
    if file_path is None:
        return None, None

    text = read_tail(file_path, config.TAIL_BYTES)
    lines = text.splitlines()

    for pattern, label in config.ERROR_PATTERNS:
        # Turn plain text into a list with one item
        if isinstance(pattern, str):
            needed = [pattern]
        else:
            needed = pattern

        for line in lines:
            all_found = True
            for word in needed:
                if word not in line:
                    all_found = False
                    break

            if all_found:
                return label, line.strip().strip("|").strip()

    return None, None


# Read the last electronic step line in OSZICAR.
# Return (dE, d eps) as numbers, or (None, None) if not readable.
# Example line:
# DAV:   3    -0.28476E+03   -0.43210E-05   -0.12345E-05  4000 ...
#              total energy   dE             d eps
def get_last_scf_values(oszicar_path):
    last_line = None
    for line in read_lines(oszicar_path):
        if is_scf_line(line):
            last_line = line.strip()

    if last_line is None:
        return None, None

    # Remove the start text, so "CG :" and "DAV:" are handled the same
    for start in config.SCF_LINE_STARTS:
        if last_line.startswith(start):
            last_line = last_line[len(start):]
            break

    # Remaining words: step number, total energy, dE, d eps, ...
    words = last_line.split()
    if len(words) < 4:
        return None, None

    try:
        d_energy = float(words[2])
        d_eps = float(words[3])
    except ValueError:
        # VASP prints stars when a number is too large to fit
        return None, None

    return d_energy, d_eps

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


# Return the largest absolute stress component from the last in kB line.
# Return None if no stress line is found.
def get_max_stress(outcar_path):
    text = read_tail(outcar_path, config.TAIL_BYTES)
    last_line = None

    for line in text.splitlines():
        if config.STRESS_TEXT in line:
            last_line = line

    if last_line is None:
        return None

    # Words after "in kB": XX YY ZZ XY YZ ZX
    after = last_line.split(config.STRESS_TEXT)[1].split()
    largest = None
    for word in after[:6]:
        try:
            value = abs(float(word))
        except ValueError:
            continue
        if largest is None or value > largest:
            largest = value

    return largest

# Run this file directly to test all functions on one directory.
# Example: python3 parse.py /path/to/one/calculation
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 parse.py /path/to/one/calculation")
        sys.exit(1)

    calc_dir = sys.argv[1]
    outcar = os.path.join(calc_dir, config.OUTCAR_NAME)
    oszicar = os.path.join(calc_dir, config.OSZICAR_NAME)

    print("Directory: " + calc_dir)

    for tag in config.KEY_INCAR_TAGS:
        print("  INCAR " + tag + ": " + str(get_incar_value(calc_dir, tag)))

    scheme, mesh = get_kpoints_info(calc_dir)
    print("  KPOINTS: " + scheme + " " + mesh)

    slurm_path, job_id = find_latest_slurm(calc_dir)
    print("  Latest slurm file: " + str(slurm_path))
    print("  Job ID: " + str(job_id))
    print("  Error label: " + str(find_error(slurm_path)))

    print("  Normal end: " + str(has_normal_end(outcar)))
    print("  Relax done: " + str(is_relax_done(outcar)))
    print("  Last SCF steps: " + str(count_last_scf_steps(oszicar)))
    print("  energy(sigma->0): " + str(get_final_energy(outcar)))
