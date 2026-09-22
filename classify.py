# classify.py
# Decide one status for each calculation directory.
# Uses scan.py to find directories and parse.py to read files.

import getpass
import os
import subprocess
import sys

import config
import parse
import scan


# Ask SLURM which of my jobs are running or pending.
# Return a set of their working directories.
# Return an empty set if squeue is not available.
def get_queued_dirs():
    user = getpass.getuser()
    command = ["squeue", "-u", user, "-h", "-o", "%Z"]

    try:
        result = subprocess.run(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
    except FileNotFoundError:
        print("Warning: squeue not found. Queue check skipped.")
        return set()

    if result.returncode != 0:
        print("Warning: squeue failed. Queue check skipped.")
        return set()

    queued = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if line != "":
            # realpath removes links, so paths compare correctly
            queued.add(os.path.realpath(line))

    return queued


# Convert INCAR text such as "100" to an integer.
# Return default if the value is missing or not a number.
def to_int(value, default):
    if value is None:
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


# Convert INCAR text such as "1E-05" to a number.
# Return default if the value is missing or not a number.
def to_float(value, default):
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


# Decide if the last electronic loop converged.
# Fewer steps than NELM: converged.
# Steps equal to NELM: converged only if dE and d eps are below EDIFF.
def scf_converged(calc_dir, oszicar_path, nelm):
    steps = parse.count_last_scf_steps(oszicar_path)
    if steps < nelm:
        return True

    d_energy, d_eps = parse.get_last_scf_values(oszicar_path)
    if d_energy is None:
        return False

    ediff = to_float(parse.get_incar_value(calc_dir, "EDIFF"),
                     config.DEFAULT_EDIFF)

    return abs(d_energy) < ediff and abs(d_eps) < ediff


# After a ZBRENT crash, check if the relaxation criteria look met.
# Forces or energy are checked always. Stress is checked if ISIF >= 3.
# Return (met, note text).
def zbrent_check(calc_dir, outcar_path, oszicar_path):
    ediff = to_float(parse.get_incar_value(calc_dir, "EDIFF"),
                     config.DEFAULT_EDIFF)
    # VASP default EDIFFG is 10 times EDIFF
    ediffg = to_float(parse.get_incar_value(calc_dir, "EDIFFG"),
                      ediff * 10)
    isif = to_int(parse.get_incar_value(calc_dir, "ISIF"), 2)

    max_force = parse.get_max_force(outcar_path)
    energy_change = parse.get_last_ionic_energy_change(oszicar_path)

    # Part 1: forces for negative EDIFFG, energy change otherwise
    if ediffg < 0:
        limit = abs(ediffg)
        met = max_force is not None and max_force < limit
        rule = "force limit " + str(limit) + " eV/A"
    else:
        limit = ediffg
        met = energy_change is not None and energy_change < limit
        rule = "energy limit " + str(limit) + " eV"

    if max_force is None:
        force_text = "max force not found"
    else:
        force_text = "max force " + "%.4f" % max_force + " eV/A"

    if energy_change is None:
        energy_text = "last ionic dE not found"
    else:
        energy_text = "last ionic dE " + "%.2e" % energy_change + " eV"

    parts = [force_text]

    # Part 2: stress, only when the cell is allowed to relax
    if isif >= 3:
        max_stress = parse.get_max_stress(outcar_path)
        stress_limit = config.STRESS_LIMIT_KB
        if max_stress is None:
            parts.append("max stress not found")
            met = False
        else:
            parts.append("max stress " + "%.2f" % max_stress + " kB (limit "
                         + str(stress_limit) + " kB)")
            if max_stress >= stress_limit:
                met = False

    parts.append(energy_text)
    parts.append(rule)

    if met:
        verdict = "criteria met, check manually"
    else:
        verdict = "criteria not met"

    note = ", ".join(parts) + ": " + verdict
    return met, note


# Compare the POTCAR elements with the POSCAR element line.
# Return (labels text, ok, note).
# ok is True for a match, False for a mismatch, None if not checked.
def potcar_check(calc_dir):
    labels = parse.get_potcar_labels(calc_dir)
    elements = parse.get_poscar_elements(calc_dir)
    labels_text = " ".join(labels)

    if len(labels) == 0:
        return labels_text, None, "POTCAR missing or unreadable"

    if len(elements) == 0:
        return labels_text, None, "POSCAR has no element line"

    # W_pv becomes W, Re becomes Re
    potcar_elements = []
    for label in labels:
        potcar_elements.append(label.split("_")[0])

    if potcar_elements == elements:
        return labels_text, True, None

    note = ("POTCAR order " + " ".join(potcar_elements)
            + " differs from POSCAR " + " ".join(elements))
    return labels_text, False, note


# Search the slurm file first, then OUTCAR, for error text.
# Return (label, file name, line), or (None, None, None).
def find_error_in_files(slurm_path, outcar_path):
    files_to_check = [slurm_path, outcar_path]

    for file_path in files_to_check:
        if file_path is None:
            continue
        if not os.path.isfile(file_path):
            continue

        label, line = parse.find_error_details(file_path)
        if label is not None:
            return label, os.path.basename(file_path), line

    return None, None, None


# Return True if the relaxation marker is in OUTCAR or the slurm file.
def relax_done_in_files(slurm_path, outcar_path):
    if parse.is_relax_done(outcar_path):
        return True

    if slurm_path is not None:
        text = parse.read_tail(slurm_path, config.TAIL_BYTES)
        if config.RELAX_DONE_TEXT in text:
            return True

    return False


# Build the record for one directory and decide its status.
# Return a dictionary with all values the report needs.
def classify(calc_dir, queued_dirs):
    outcar_path = os.path.join(calc_dir, config.OUTCAR_NAME)
    oszicar_path = os.path.join(calc_dir, config.OSZICAR_NAME)
    slurm_path, job_id = parse.find_latest_slurm(calc_dir)
    scheme, mesh = parse.get_kpoints_info(calc_dir)

    record = {}
    record["path"] = calc_dir
    record["status"] = ""
    record["job_id"] = job_id
    record["energy"] = None
    record["kpoints_scheme"] = scheme
    record["kpoints_mesh"] = mesh
    record["missing"] = scan.find_missing_inputs(calc_dir)
    record["message_label"] = None
    record["message_file"] = None
    record["message_line"] = None
    record["scf_at_nelm"] = False
    record["zbrent_met"] = False
    record["zbrent_note"] = None

    # Store the key INCAR tags, for example record["ENCUT"] = "350"
    for tag in config.KEY_INCAR_TAGS:
        record[tag] = parse.get_incar_value(calc_dir, tag)

    # Check POTCAR against POSCAR for every folder, even before running
    labels, ok, note = potcar_check(calc_dir)
    record["potcar_labels"] = labels
    record["potcar_ok"] = ok
    record["potcar_note"] = note

    # Step 1: job is still in the queue
    if os.path.realpath(calc_dir) in queued_dirs:
        record["status"] = config.STATUS_RUNNING
        return record

    # Step 2: no output at all
    outcar_exists = os.path.isfile(outcar_path)
    if not outcar_exists and slurm_path is None:
        if len(record["missing"]) > 0:
            record["status"] = config.STATUS_MISSING_INPUTS
        else:
            record["status"] = config.STATUS_NOT_SUBMITTED
        return record

    # Search both files for error text. Kept for every status below.
    label, file_name, line = find_error_in_files(slurm_path, outcar_path)
    record["message_label"] = label
    record["message_file"] = file_name
    record["message_line"] = line

    # Read NELM and NSW once. Used by the steps below.
    nelm = to_int(record["NELM"], config.DEFAULT_NELM)
    nsw = to_int(parse.get_incar_value(calc_dir, "NSW"), 0)

    # Note if the last electronic loop hit NELM without converging.
    scf_ok = scf_converged(calc_dir, oszicar_path, nelm)
    if not scf_ok:
        record["scf_at_nelm"] = True

    # Step 3: VASP did not finish normally
    if not parse.has_normal_end(outcar_path):
        if label is not None:
            record["status"] = config.STATUS_CRASHED
        else:
            record["status"] = config.STATUS_INCOMPLETE

        # For ZBRENT crashes, check how close the relaxation got.
        if label == config.ZBRENT_LABEL:
            met, note = zbrent_check(calc_dir, outcar_path, oszicar_path)
            record["zbrent_met"] = met
            record["zbrent_note"] = note

        return record

    # Step 4: VASP finished normally. Check convergence.
    record["energy"] = parse.get_final_energy(outcar_path)

    if not scf_ok:
        record["status"] = config.STATUS_SCF_NOT_CONVERGED
    elif nsw > 0 and not relax_done_in_files(slurm_path, outcar_path):
        record["status"] = config.STATUS_IONIC_NOT_CONVERGED
    else:
        record["status"] = config.STATUS_CONVERGED

    return record


# Classify every calculation directory under root.
# Return a list of records.
def classify_all(root):
    queued_dirs = get_queued_dirs()
    calc_dirs = scan.find_calc_dirs(root)

    records = []
    for calc_dir in calc_dirs:
        records.append(classify(calc_dir, queued_dirs))

    return records


# Run this file directly to test.
# Example: python3 classify.py /path/to/calculations
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 classify.py /path/to/calculations")
        sys.exit(1)

    records = classify_all(sys.argv[1])

    # Count directories per status
    counts = {}
    for record in records:
        status = record["status"]
        counts[status] = counts.get(status, 0) + 1

    print("Directories: " + str(len(records)))
    for status in sorted(counts):
        print("  " + status + ": " + str(counts[status]))

    print("")
    for record in records:
        text = record["status"] + " | " + record["path"]
        if record["scf_at_nelm"]:
            text = text + " [SCF at NELM]"
        print(text)
        if record["message_label"] is not None:
            print("    " + record["message_file"] + ": "
                  + record["message_line"])
        if record["zbrent_note"] is not None:
            print("    " + record["zbrent_note"])
        if record["potcar_ok"] is False:
            print("    " + record["potcar_note"])