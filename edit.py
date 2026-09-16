# edit.py
# Change INCAR and KPOINTS in selected calculation folders.
# Shows every change first and writes only after you type yes.
# Each folder is saved with history.py before it is changed.

import argparse
import os
import sys

import classify
import config
import history
import parse


# Return every status label used by the tool.
def all_statuses():
    statuses = []
    for group_name, group_statuses in config.REPORT_GROUPS:
        for status in group_statuses:
            statuses.append(status)
    return statuses


# Read folder paths from a text file, one per line.
# Empty lines and lines starting with # are ignored.
def read_dir_list(list_path):
    dirs = []
    for line in parse.read_lines(list_path):
        line = line.strip()
        if line == "" or line.startswith("#"):
            continue
        dirs.append(line)
    return dirs


# Return the folders to edit, chosen by status or by a list file.
def select_dirs(status, root, list_path):
    selected = []

    if status is not None:
        for record in classify.classify_all(root):
            if record["status"] == status:
                selected.append(record["path"])

    if list_path is not None:
        selected = read_dir_list(list_path)

    return selected


# Turn items like "EDIFF=1E-7" into pairs like ("EDIFF", "1E-7").
# Stop the program if an item is written wrongly.
def parse_set_items(items):
    pairs = []
    for item in items:
        if "=" not in item:
            print("Error: use TAG=VALUE, not: " + item)
            sys.exit(1)

        key, value = item.split("=", 1)
        key = key.strip().upper()
        value = value.strip()

        if key == "" or value == "":
            print("Error: empty tag or value in: " + item)
            sys.exit(1)

        pairs.append((key, value))
    return pairs


# Split one INCAR line into its content and its comment.
# Example: "NELM = 60 # note" gives ("NELM = 60 ", "# note")
def split_comment(line):
    position = len(line)
    for mark in ["#", "!"]:
        index = line.find(mark)
        if index != -1 and index < position:
            position = index
    return line[:position], line[position:]


# Work out the new INCAR lines without writing anything.
# sets    : list of (TAG, VALUE) to change or add
# removes : list of TAG names to delete
# Return (new lines, list of change descriptions).
def plan_incar(lines, sets, removes):
    set_values = {}
    for key, value in sets:
        set_values[key] = value

    new_lines = []
    changes = []
    found = []

    for line in lines:
        text = line.rstrip("\n")
        content, comment = split_comment(text)
        parts = content.split(";")

        new_parts = []
        line_changed = False

        for part in parts:
            if "=" not in part:
                new_parts.append(part)
                continue

            name, value = part.split("=", 1)
            key = name.strip().upper()
            old_value = value.strip()

            # Delete this tag
            if key in removes:
                changes.append("remove " + key + " (was "
                               + old_value + ")")
                line_changed = True
                continue

            # Change this tag
            if key in set_values:
                found.append(key)
                new_value = set_values[key]
                if new_value != old_value:
                    changes.append(key + ": " + old_value + " -> "
                                   + new_value)
                    new_parts.append(key + " = " + new_value)
                    line_changed = True
                    continue

            new_parts.append(part)

        # Line not touched: keep it exactly as it was
        if not line_changed:
            new_lines.append(text + "\n")
            continue

        # Line touched: rebuild it from the parts that remain
        kept = []
        for part in new_parts:
            if part.strip() != "":
                kept.append(part.strip())

        if len(kept) == 0:
            # Only a comment is left, or nothing at all
            if comment.strip() != "":
                new_lines.append(comment + "\n")
            continue

        rebuilt = " ; ".join(kept)
        if comment != "":
            rebuilt = rebuilt + "   " + comment
        new_lines.append(rebuilt + "\n")

    # Tags that were not in the INCAR are added at the end
    for key, value in sets:
        if key not in found:
            changes.append(key + ": not set -> " + value)
            new_lines.append(key + " = " + value + "\n")

    return new_lines, changes


# Build the text of a new automatic KPOINTS file.
def make_kpoints_text(scheme_name, mesh):
    lines = []
    lines.append("Automatic mesh written by vasp_triage")
    lines.append("0")
    lines.append(scheme_name)
    lines.append("  " + mesh)
    lines.append("  0 0 0")
    return "\n".join(lines) + "\n"


# Rename WAVECAR to WAVECAR_old, or WAVECAR_old_2 if that exists.
# Return the new name, or None if there was no WAVECAR.
def rename_wavecar(calc_dir):
    source = os.path.join(calc_dir, config.WAVECAR_NAME)
    if not os.path.isfile(source):
        return None

    new_name = config.WAVECAR_NAME + "_old"
    number = 2
    while os.path.exists(os.path.join(calc_dir, new_name)):
        new_name = config.WAVECAR_NAME + "_old_" + str(number)
        number = number + 1

    os.rename(source, os.path.join(calc_dir, new_name))
    return new_name


# Write a list of lines to a file, replacing its content.
def write_lines(file_path, lines):
    with open(file_path, "w") as f:
        f.writelines(lines)


# Read and check the command line options.
def read_arguments():
    parser = argparse.ArgumentParser(
        description="Change INCAR and KPOINTS in selected folders.")

    parser.add_argument("--status",
                        help="edit folders with this status")
    parser.add_argument("--root",
                        help="calculation root, needed with --status")
    parser.add_argument("--list",
                        help="text file with one folder path per line")
    parser.add_argument("--set", action="append", default=[],
                        help="TAG=VALUE, can be used many times")
    parser.add_argument("--remove", action="append", default=[],
                        help="TAG to delete, can be used many times")
    parser.add_argument("--kpoints", nargs=4,
                        metavar=("SCHEME", "N1", "N2", "N3"),
                        help="gamma or mp, then three integers")

    args = parser.parse_args()

    # Exactly one way of choosing folders
    if args.status is None and args.list is None:
        print("Error: give --status or --list.")
        sys.exit(1)
    if args.status is not None and args.list is not None:
        print("Error: give only one of --status or --list.")
        sys.exit(1)
    if args.status is not None and args.root is None:
        print("Error: --status needs --root.")
        sys.exit(1)
    if args.status is not None and args.status not in all_statuses():
        print("Error: unknown status. Use one of:")
        for status in all_statuses():
            print("  " + status)
        sys.exit(1)

    # At least one change
    if (len(args.set) == 0 and len(args.remove) == 0
            and args.kpoints is None):
        print("Error: give --set, --remove, or --kpoints.")
        sys.exit(1)

    return args


if __name__ == "__main__":
    args = read_arguments()

    sets = parse_set_items(args.set)

    removes = []
    for key in args.remove:
        removes.append(key.strip().upper())

    for key, value in sets:
        if key in removes:
            print("Error: " + key + " is in both --set and --remove.")
            sys.exit(1)

    # Check the KPOINTS option
    new_scheme = None
    new_mesh = None
    if args.kpoints is not None:
        scheme_word = args.kpoints[0].lower()
        if scheme_word == "gamma":
            new_scheme = "Gamma"
        elif scheme_word == "mp":
            new_scheme = "Monkhorst Pack"
        else:
            print("Error: KPOINTS scheme must be gamma or mp.")
            sys.exit(1)

        for number in args.kpoints[1:]:
            if not number.isdigit() or int(number) < 1:
                print("Error: mesh values must be positive integers.")
                sys.exit(1)
        new_mesh = " ".join(args.kpoints[1:])

    dirs = select_dirs(args.status, args.root, args.list)
    if len(dirs) == 0:
        print("No folders selected.")
        sys.exit(0)

    queued_dirs = classify.get_queued_dirs()

    # Step 1: plan every change and show it. Nothing is written yet.
    plans = []
    for calc_dir in dirs:
        incar_path = os.path.join(calc_dir, config.INCAR_NAME)

        if not os.path.isfile(incar_path):
            print("No INCAR, skipped: " + calc_dir)
            continue
        if os.path.realpath(calc_dir) in queued_dirs:
            print("Running, skipped: " + calc_dir)
            continue

        old_lines = parse.read_lines(incar_path)
        new_lines, changes = plan_incar(old_lines, sets, removes)

        kpoints_text = None
        if new_scheme is not None:
            old_scheme, old_mesh = parse.get_kpoints_info(calc_dir)
            if old_scheme != new_scheme or old_mesh != new_mesh:
                changes.append("KPOINTS: " + old_scheme + " " + old_mesh
                               + " -> " + new_scheme + " " + new_mesh)
                kpoints_text = make_kpoints_text(new_scheme, new_mesh)

        if len(changes) == 0:
            print("No change needed: " + calc_dir)
            continue

        print("")
        print(calc_dir)
        for change in changes:
            print("  " + change)

        plans.append((calc_dir, new_lines, kpoints_text))

    if len(plans) == 0:
        print("Nothing to change.")
        sys.exit(0)

    # Step 2: ask once for all folders
    print("")
    print("Folders to change: " + str(len(plans)))
    answer = input("Type yes to save each run and apply the changes: ")
    if answer.strip() != "yes":
        print("Cancelled. No files changed.")
        sys.exit(0)

    # Step 3: save the old run, then write the new files
    for calc_dir, new_lines, kpoints_text in plans:
        history.archive_one(calc_dir, queued_dirs)

        incar_path = os.path.join(calc_dir, config.INCAR_NAME)
        write_lines(incar_path, new_lines)

        if kpoints_text is not None:
            kpoints_path = os.path.join(calc_dir, config.KPOINTS_NAME)
            write_lines(kpoints_path, [kpoints_text])

            renamed = rename_wavecar(calc_dir)
            if renamed is not None:
                print("  WAVECAR renamed to " + renamed)

        print("Changed: " + calc_dir)
