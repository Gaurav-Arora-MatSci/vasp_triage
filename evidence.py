# evidence.py
# Collect the numbers the decision agent needs for one folder.
# Every function only reads files inside that folder.
# Nothing here decides what to do. decide.py does that.

import filecmp
import os
import sys

import classify
import config
import parse


# Split one electronic step line of OSZICAR into numbers.
# Return a dictionary with energy, dE, d eps, the method (DAV, RMM,
# or CG), and mixed, or None if the line cannot be read.
# mixed is True when the line has the rms(c) column. VASP prints it
# only for steps where the charge density was mixed, so the first
# steps without it used a fixed density.
def scf_numbers(line):
    text = line.strip()
    method = ""
    for start in config.SCF_LINE_STARTS:
        if text.startswith(start):
            text = text[len(start):]
            method = start.replace(":", "").strip()
            break

    # Remaining words: step, energy, dE, d eps, ncg, rms, rms(c)
    words = text.split()
    if len(words) < 4:
        return None

    try:
        energy = float(words[1])
        d_energy = float(words[2])
        d_eps = float(words[3])
    except ValueError:
        # VASP prints stars when a number is too large to fit
        return None

    return {"energy": energy, "dE": d_energy, "d_eps": d_eps,
            "method": method, "mixed": len(words) >= 7}


# Read the F= energy from one ionic line of OSZICAR.
# Return None if it cannot be read.
def ionic_energy(line):
    after = line.split("F=")[1].split()
    if len(after) == 0:
        return None
    try:
        return float(after[0])
    except ValueError:
        return None


# Read OSZICAR into a list of ionic steps.
# Each step is a dictionary:
#   "scf": list of scf_numbers dictionaries, one per electronic step
#   "energy": the F= energy, or None if the step did not finish
def read_oszicar(oszicar_path):
    steps = []
    current = []

    for line in parse.read_lines(oszicar_path):
        if parse.is_scf_line(line):
            numbers = scf_numbers(line)
            if numbers is not None:
                current.append(numbers)
        elif "F=" in line:
            steps.append({"scf": current, "energy": ionic_energy(line)})
            current = []

    # The file ended inside an ionic step
    if len(current) > 0:
        steps.append({"scf": current, "energy": None})

    return steps


# Return the F= energies of the finished ionic steps, in order.
def ionic_energies(oszicar_path):
    energies = []
    for step in read_oszicar(oszicar_path):
        if step["energy"] is not None:
            energies.append(step["energy"])
    return energies


# Return the largest force of every TOTAL-FORCE block in OUTCAR, in
# order, one value per ionic step. Reads the whole file line by line.
def all_max_forces(outcar_path):
    forces = []
    if not os.path.isfile(outcar_path):
        return forces

    reading = False
    dash_count = 0
    block_max = 0.0

    with open(outcar_path, "r", errors="replace") as f:
        for line in f:
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
                    forces.append(block_max)
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

    return forces


# Return the final F= energy of the run before the current one.
# Archived copies are named OSZICAR-1, OSZICAR-2, and so on. A copy
# identical to the current OSZICAR is the current run already saved
# by vtriage history, so it is skipped.
# Return None if there is no earlier run with an energy.
def previous_run_energy(calc_dir):
    oszicar = os.path.join(calc_dir, config.OSZICAR_NAME)
    prefix = config.OSZICAR_NAME + "-"

    numbers = []
    for name in os.listdir(calc_dir):
        if not name.startswith(prefix):
            continue
        number = name[len(prefix):]
        if number.isdigit():
            numbers.append(int(number))

    numbers.sort()
    numbers.reverse()

    for number in numbers:
        saved = os.path.join(calc_dir, prefix + str(number))
        if os.path.isfile(oszicar):
            if filecmp.cmp(oszicar, saved, shallow=False):
                continue

        energies = ionic_energies(saved)
        if len(energies) > 0:
            return energies[-1]

    return None


# Check that CONTCAR holds a position line for every atom.
# A job killed while VASP wrote CONTCAR can leave it cut short.
# Return True if it looks complete.
def contcar_complete(calc_dir):
    contcar = os.path.join(calc_dir, config.CONTCAR_NAME)
    lines = parse.read_lines(contcar)
    if len(lines) < 8:
        return False

    # Line 7 holds the atom counts, for example 54 2
    total = 0
    for word in lines[6].split():
        if not word.isdigit():
            return False
        total = total + int(word)

    # Line 8 is Selective dynamics or the coordinate type
    first = 8
    if lines[7].strip().lower().startswith("s"):
        first = 9

    count = 0
    for line in lines[first:first + total]:
        if len(line.split()) >= 3:
            count = count + 1

    return count == total


# Return the number of atoms from line 7 of POSCAR, or None if the
# line does not hold the atom counts.
def atom_count(calc_dir):
    poscar = os.path.join(calc_dir, config.POSCAR_NAME)
    lines = parse.read_lines(poscar)
    if len(lines) < 7:
        return None

    total = 0
    for word in lines[6].split():
        if not word.isdigit():
            return None
        total = total + int(word)

    if total == 0:
        return None
    return total


# Label each electronic step of one loop with its phase.
# The steps before the first step with rms(c) used a fixed density.
# After that, every step counts as density updated, also the last
# step, which VASP prints without rms(c) when it stops.
# If no step has rms(c), the phases are unknown and left empty, so
# they cannot mislead.
# A change of method, such as DAV to RMM, is noted on its step.
# Return a list of labels, one per step.
def scf_phases(loop):
    first_mixed = None
    for index in range(len(loop)):
        if loop[index]["mixed"]:
            first_mixed = index
            break

    labels = []
    for index in range(len(loop)):
        if first_mixed is None:
            label = ""
        elif index < first_mixed:
            label = "fixed density"
        else:
            label = "density updated"

        if index > 0:
            before = loop[index - 1]["method"]
            now = loop[index]["method"]
            if before != now and before != "" and now != "":
                if label == "":
                    label = before + " to " + now
                else:
                    label = label + ", " + before + " to " + now

        labels.append(label)
    return labels


# Return an INCAR value as text, or "not set".
def incar_text(calc_dir, tag):
    value = parse.get_incar_value(calc_dir, tag)
    if value is None:
        return "not set"
    return value


# Format a number for the evidence table.
def number_text(value, pattern):
    if value is None:
        return "n/a"
    return pattern % value


# Build the evidence text for an ionic relaxation that did not reach
# EDIFFG. Shows up to AGENT_EVIDENCE_STEPS of the latest ionic steps.
def ionic_evidence(calc_dir):
    oszicar = os.path.join(calc_dir, config.OSZICAR_NAME)
    outcar = os.path.join(calc_dir, config.OUTCAR_NAME)

    steps = read_oszicar(oszicar)
    forces = all_max_forces(outcar)

    finished = []
    for step in steps:
        if step["energy"] is not None:
            finished.append(step)

    lines = []
    tags = ["NSW", "IBRION", "ISIF", "POTIM", "EDIFF", "EDIFFG",
            "NELM", "ALGO"]
    tag_parts = []
    for tag in tags:
        tag_parts.append(tag + "=" + incar_text(calc_dir, tag))
    lines.append("INCAR: " + ", ".join(tag_parts))

    lines.append("Finished ionic steps in this run: "
                 + str(len(finished)))

    if len(finished) > 0:
        first = finished[0]["energy"]
        last = finished[-1]["energy"]
        lines.append("Energy first step: " + "%.6f" % first
                     + " eV, last step: " + "%.6f" % last
                     + " eV, change: " + "%.6f" % (last - first) + " eV")

    isif = classify.to_int(parse.get_incar_value(calc_dir, "ISIF"), 2)
    if isif >= 3:
        stress = parse.get_max_stress(outcar)
        lines.append("Largest stress component, last step: "
                     + number_text(stress, "%.2f") + " kB")

    lines.append("Columns: step | F energy (eV) | change from previous"
                 " step (eV) | max force (eV/A) | electronic steps")

    count = len(finished)
    start = count - config.AGENT_EVIDENCE_STEPS
    if start < 0:
        start = 0

    for index in range(start, count):
        energy = finished[index]["energy"]
        if index == 0:
            change = None
        else:
            change = energy - finished[index - 1]["energy"]

        force = None
        if index < len(forces):
            force = forces[index]

        lines.append(str(index + 1) + " | " + "%.6f" % energy + " | "
                     + number_text(change, "%.2e") + " | "
                     + number_text(force, "%.4f") + " | "
                     + str(len(finished[index]["scf"])))

    return "\n".join(lines)


# Build the evidence text for a run whose last electronic loop hit
# NELM without reaching EDIFF.
def scf_evidence(calc_dir):
    oszicar = os.path.join(calc_dir, config.OSZICAR_NAME)
    steps = read_oszicar(oszicar)

    nelm = classify.to_int(parse.get_incar_value(calc_dir, "NELM"),
                           config.DEFAULT_NELM)

    lines = []
    tags = ["NELM", "EDIFF", "ALGO", "ISMEAR", "SIGMA", "AMIX", "BMIX",
            "NSW", "ISPIN"]
    tag_parts = []
    for tag in tags:
        tag_parts.append(tag + "=" + incar_text(calc_dir, tag))
    lines.append("INCAR: " + ", ".join(tag_parts))

    # How many electronic loops in this run hit NELM
    at_limit = 0
    for step in steps:
        if len(step["scf"]) >= nelm:
            at_limit = at_limit + 1
    lines.append("Ionic steps in this run: " + str(len(steps))
                 + ", electronic loops that hit NELM: " + str(at_limit))

    if len(steps) == 0:
        lines.append("No electronic steps found in OSZICAR.")
        return "\n".join(lines)

    last_loop = steps[-1]["scf"]
    phases = scf_phases(last_loop)
    lines.append("Last electronic loop, " + str(len(last_loop))
                 + " steps.")

    fixed = 0
    for label in phases:
        if label.startswith("fixed density"):
            fixed = fixed + 1
    if fixed > 0:
        lines.append("Steps 1 to " + str(fixed) + " used a fixed"
                     " density. The density is updated from step "
                     + str(fixed + 1) + ".")
    for index in range(len(phases)):
        if " to " in phases[index]:
            switch = phases[index].split(", ")[-1]
            lines.append("The method switched " + switch + " at step "
                         + str(index + 1) + ".")

    lines.append("Columns: step | energy (eV) | dE (eV) | d eps | phase")

    # Show the first few steps and the latest ones
    count = len(last_loop)
    shown = []
    for index in range(count):
        if index < 5 or index >= count - config.AGENT_EVIDENCE_STEPS:
            shown.append(index)

    previous = -1
    for index in shown:
        if index != previous + 1:
            lines.append("...")
        step = last_loop[index]
        lines.append(str(index + 1) + " | " + "%.6f" % step["energy"]
                     + " | " + "%.2e" % step["dE"] + " | "
                     + "%.2e" % step["d_eps"] + " | " + phases[index])
        previous = index

    return "\n".join(lines)


# Run this file directly to see the evidence for one folder.
# Example: python3 evidence.py /path/to/one/calculation
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 evidence.py /path/to/one/calculation")
        sys.exit(1)

    calc_dir = sys.argv[1]
    print("Ionic evidence:")
    print(ionic_evidence(calc_dir))
    print("")
    print("SCF evidence:")
    print(scf_evidence(calc_dir))
    print("")
    print("Previous run energy: " + str(previous_run_energy(calc_dir)))
