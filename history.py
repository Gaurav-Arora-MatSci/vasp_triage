# history.py
# Save a finished run and record it in progress.txt.
# Files are copied, not moved, to name-N, for example OUTCAR-2.
# A folder is skipped if its job is running or it was already saved.

import datetime
import filecmp
import os
import shutil
import sys

import classify
import config
import parse
import scan


# Find the highest run number already used in a folder.
# Looks at archive names such as OUTCAR-3 and Run lines in progress.txt.
# Return 0 if nothing was archived yet.
def last_run_number(calc_dir):
    highest = 0

    for name in os.listdir(calc_dir):
        for base in config.ARCHIVE_FILES:
            prefix = base + "-"
            if not name.startswith(prefix):
                continue
            number = name[len(prefix):]
            if number.isdigit() and int(number) > highest:
                highest = int(number)

    progress_path = os.path.join(calc_dir, config.PROGRESS_NAME)
    for line in parse.read_lines(progress_path):
        if not line.startswith("Run "):
            continue
        number = line.split("|")[0].replace("Run", "").strip()
        if number.isdigit() and int(number) > highest:
            highest = int(number)

    return highest


# Read the job ID from the last Run line in progress.txt.
# Return None if progress.txt is missing or has no job ID.
def last_recorded_job_id(calc_dir):
    progress_path = os.path.join(calc_dir, config.PROGRESS_NAME)
    job_id = None

    for line in parse.read_lines(progress_path):
        if not line.startswith("Run "):
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        value = parts[2].replace("Job", "").strip()
        if value.isdigit():
            job_id = value
        else:
            job_id = None

    return job_id

# Read all Run blocks from progress.txt.
# Return a list of dictionaries with job_id, result, and label.
def read_progress_blocks(calc_dir):
    progress_path = os.path.join(calc_dir, config.PROGRESS_NAME)
    blocks = []
    current = None

    for line in parse.read_lines(progress_path):
        text = line.strip()

        # A Run line starts a new block
        if text.startswith("Run "):
            current = {"job_id": None, "result": None, "label": None}
            blocks.append(current)
            parts = text.split("|")
            if len(parts) >= 3:
                value = parts[2].replace("Job", "").strip()
                if value.isdigit():
                    current["job_id"] = value
            continue

        if current is None:
            continue

        if text.startswith("Result:"):
            current["result"] = text[len("Result:"):].strip()
        elif text.startswith("Message:"):
            message = text[len("Message:"):].strip()
            if message != "none":
                # Label is the text before " (file): line"
                current["label"] = message.split(" (")[0].strip()

    return blocks


# Return the error label of the previous crashed run, or None.
# The current run is ignored, even if it was already archived.
def previous_crash_label(calc_dir, current_job_id):
    earlier = []
    for block in read_progress_blocks(calc_dir):
        if current_job_id is not None and block["job_id"] == current_job_id:
            continue
        earlier.append(block)

    if len(earlier) == 0:
        return None

    last = earlier[-1]
    if last["result"] != config.STATUS_CRASHED:
        return None

    return last["label"]


# Decide whether the current run was already saved.
# Return True if it was saved, False if it is new.
def is_already_archived(calc_dir, job_id):
    last_number = last_run_number(calc_dir)
    if last_number == 0:
        return False

    # Case 1: a slurm file exists. Compare job IDs.
    if job_id is not None:
        return job_id == last_recorded_job_id(calc_dir)

    # Case 2: no slurm file. Compare OUTCAR with the last saved copy.
    outcar = os.path.join(calc_dir, config.OUTCAR_NAME)
    saved = outcar + "-" + str(last_number)
    if os.path.isfile(outcar) and os.path.isfile(saved):
        return filecmp.cmp(outcar, saved, shallow=False)

    return False


# Copy each archive file that exists to name-N.
# Return the list of new file names.
def copy_run_files(calc_dir, run_number):
    copied = []

    for name in config.ARCHIVE_FILES:
        source = os.path.join(calc_dir, name)
        if not os.path.isfile(source):
            continue

        target_name = name + "-" + str(run_number)
        target = os.path.join(calc_dir, target_name)

        # Never overwrite an existing archive file.
        if os.path.exists(target):
            print("Warning: " + target + " exists. Not overwritten.")
            continue

        # copy2 keeps the original file date.
        shutil.copy2(source, target)
        copied.append(target_name)

    return copied


# Return the current time as text, for example 16 Sept 2026 1:16 PM
def time_text():
    now = datetime.datetime.now()
    month = config.MONTH_NAMES[now.month - 1]

    hour = now.hour % 12
    if hour == 0:
        hour = 12
    if now.hour < 12:
        am_pm = "AM"
    else:
        am_pm = "PM"

    return (str(now.day) + " " + month + " " + str(now.year) + " "
            + str(hour) + ":" + now.strftime("%M") + " " + am_pm)


# Build the text block for one run in progress.txt.
def make_progress_block(run_number, record, copied):
    job_text = "none"
    if record["job_id"] is not None:
        job_text = record["job_id"]

    lines = []
    lines.append("Run " + str(run_number) + " | " + time_text()
                 + " | Job " + job_text)

    for tag in config.KEY_INCAR_TAGS:
        value = record[tag]
        if value is None:
            value = "not set"
        lines.append("  " + tag + ": " + value)

    kpoints = (record["kpoints_scheme"] + " "
               + record["kpoints_mesh"]).strip()
    lines.append("  KPOINTS: " + kpoints)
    lines.append("  Result: " + record["status"])

    if record["energy"] is None:
        lines.append("  energy(sigma->0): not available")
    else:
        lines.append("  energy(sigma->0): " + str(record["energy"])
                     + " eV")

    if record["message_label"] is None:
        lines.append("  Message: none")
    else:
        lines.append("  Message: " + record["message_label"] + " ("
                     + record["message_file"] + "): "
                     + record["message_line"])

    if record["zbrent_note"] is not None:
        lines.append("  Note: " + record["zbrent_note"])
    lines.append("  Archived as: " + " ".join(copied))
    lines.append("")

    return "\n".join(lines) + "\n"


# Add one block to the end of progress.txt. Create the file if needed.
def append_progress(calc_dir, block):
    progress_path = os.path.join(calc_dir, config.PROGRESS_NAME)
    with open(progress_path, "a") as f:
        f.write(block)


# Save one folder if it has a new finished run.
# Return a short result word: archived, running, no output, or skipped.
def archive_one(calc_dir, queued_dirs):
    record = classify.classify(calc_dir, queued_dirs)

    # Never copy files while VASP may still write them.
    if record["status"] == config.STATUS_RUNNING:
        print("Running, skipped: " + calc_dir)
        return "running"

    # Nothing has run in this folder yet.
    outcar = os.path.join(calc_dir, config.OUTCAR_NAME)
    if not os.path.isfile(outcar) and record["job_id"] is None:
        return "no output"

    if is_already_archived(calc_dir, record["job_id"]):
        return "skipped"

    run_number = last_run_number(calc_dir) + 1
    copied = copy_run_files(calc_dir, run_number)
    block = make_progress_block(run_number, record, copied)
    append_progress(calc_dir, block)

    print("Archived as run " + str(run_number) + ": " + calc_dir)
    return "archived"


# Run this file directly to save all new finished runs under a root.
# The root can also be a single calculation folder.
# Example: python3 history.py /path/to/calculations
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 history.py /path/to/calculations")
        sys.exit(1)

    root = sys.argv[1]
    if not os.path.isdir(root):
        print("Error: not a directory: " + root)
        sys.exit(1)

    queued_dirs = classify.get_queued_dirs()
    counts = {}

    for calc_dir in scan.find_calc_dirs(root):
        result = archive_one(calc_dir, queued_dirs)
        counts[result] = counts.get(result, 0) + 1

    print("")
    print("Summary:")
    for result in sorted(counts):
        print("  " + result + ": " + str(counts[result]))
