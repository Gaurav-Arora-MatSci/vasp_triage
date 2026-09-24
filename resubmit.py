# resubmit.py
# Submit selected calculation folders with sbatch.
# Saves each old run with history.py before submitting.
# For unfinished relaxations, copies CONTCAR to POSCAR first.
# Two limits apply, and the smaller one wins:
#   --max          new jobs per run (default MAX_SUBMIT)
#   --queue-limit  my jobs in the queue at once (default QUEUE_LIMIT)

import argparse
import getpass
import os
import shutil
import subprocess
import sys

import classify
import config
import edit
import history
import parse
import scan


# Read and check the command line options.
def read_arguments():
    parser = argparse.ArgumentParser(
        description="Submit selected folders with sbatch.")

    parser.add_argument("--status",
                        help="submit folders with this status")
    parser.add_argument("--group",
                        help="submit folders in this report group")
    parser.add_argument("--root",
                        help="calculation root, needed with --status"
                             " or --group")
    parser.add_argument("--list",
                        help="text file with one folder path per line")
    parser.add_argument("--max", type=int, default=config.MAX_SUBMIT,
                        help="largest number of jobs to submit per run")
    parser.add_argument("--queue-limit", type=int,
                        default=config.QUEUE_LIMIT,
                        help="largest number of my jobs in the queue,"
                             " 0 turns it off")
    parser.add_argument("--force", action="store_true",
                        help="also submit converged folders")
    parser.add_argument("--skip-zbrent-met", action="store_true",
                        help="skip ZBRENT crashes whose criteria look met")

    args = parser.parse_args()

    choices = 0
    if args.status is not None:
        choices = choices + 1
    if args.group is not None:
        choices = choices + 1
    if args.list is not None:
        choices = choices + 1

    if choices != 1:
        print("Error: give exactly one of --status, --group, or --list.")
        sys.exit(1)

    if args.list is None and args.root is None:
        print("Error: --status and --group need --root.")
        sys.exit(1)

    if args.status is not None:
        if args.status not in edit.all_statuses():
            print("Error: unknown status. Use one of:")
            for status in edit.all_statuses():
                print("  " + status)
            sys.exit(1)

    if args.group is not None:
        if args.group not in edit.all_group_names():
            print("Error: unknown group. Use one of:")
            for name in edit.all_group_names():
                print("  " + name)
            sys.exit(1)

    if args.max < 1:
        print("Error: --max must be 1 or more.")
        sys.exit(1)

    if args.queue_limit < 0:
        print("Error: --queue-limit must be 0 or more.")
        sys.exit(1)

    return args


# Count my jobs in the queue, running and pending.
# Return None if squeue cannot be used.
def count_queued_jobs():
    user = getpass.getuser()
    command = ["squeue", "-u", user, "-h", "-o", "%i"]

    try:
        result = subprocess.run(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
    except FileNotFoundError:
        return None

    if result.returncode != 0:
        return None

    count = 0
    for line in result.stdout.splitlines():
        if line.strip() != "":
            count = count + 1

    return count


# Decide if this run should restart from CONTCAR.
# Return True only for unfinished relaxations.
def needs_contcar_restart(calc_dir, record):
    nsw = classify.to_int(parse.get_incar_value(calc_dir, "NSW"), 0)
    if nsw <= 0:
        return False

    if record["status"] == config.STATUS_IONIC_NOT_CONVERGED:
        return True

    # A run that met EDIFFG before dying is worth continuing
    if record["status"] == config.STATUS_RELAX_DONE_CRASHED:
        return True

    if record["status"] == config.STATUS_CRASHED:
        if record["message_label"] in config.CONTCAR_RESTART_LABELS:
            return True

    return False


# Check that CONTCAR can replace POSCAR.
# Return (True, "") if safe, or (False, reason) if not.
def check_contcar(calc_dir):
    contcar = os.path.join(calc_dir, config.CONTCAR_NAME)
    poscar = os.path.join(calc_dir, config.POSCAR_NAME)

    contcar_lines = parse.read_lines(contcar)
    poscar_lines = parse.read_lines(poscar)

    if len(contcar_lines) < 8:
        return False, "CONTCAR missing or empty"
    if len(poscar_lines) < 8:
        return False, "POSCAR missing or empty"

    # Lines 6 and 7 hold element names and atom counts.
    for index in [5, 6]:
        if contcar_lines[index].split() != poscar_lines[index].split():
            return False, "CONTCAR atoms differ from POSCAR"

    return True, ""


# Copy CONTCAR to POSCAR and note it in progress.txt.
def copy_contcar_to_poscar(calc_dir):
    contcar = os.path.join(calc_dir, config.CONTCAR_NAME)
    poscar = os.path.join(calc_dir, config.POSCAR_NAME)
    shutil.copy2(contcar, poscar)
    history.append_progress(calc_dir,
                            "  Next run starts from CONTCAR\n\n")


# Run sbatch inside one folder.
# Return the new job ID as text, or None if submission failed.
def submit_one(calc_dir):
    command = ["sbatch", config.JOB_SCRIPT_NAME]

    try:
        result = subprocess.run(command,
                                cwd=calc_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
    except FileNotFoundError:
        print("Error: sbatch not found.")
        return None

    if result.returncode != 0:
        print("sbatch failed in " + calc_dir)
        print("  " + result.stderr.strip())
        return None

    # sbatch prints: Submitted batch job 300200
    words = result.stdout.split()
    if len(words) == 0 or not words[-1].isdigit():
        print("Could not read job ID: " + result.stdout.strip())
        return None

    return words[-1]


if __name__ == "__main__":
    args = read_arguments()

    # Work out how many jobs may be submitted in this run.
    allowed = args.max
    if args.queue_limit > 0:
        queued_count = count_queued_jobs()
        if queued_count is None:
            print("Error: cannot count queued jobs, squeue failed.")
            print("Use --queue-limit 0 to submit without this limit.")
            sys.exit(1)

        free_slots = args.queue_limit - queued_count
        print("Jobs in queue: " + str(queued_count) + " of limit "
              + str(args.queue_limit))

        if free_slots <= 0:
            print("Queue is full. Nothing submitted.")
            sys.exit(0)

        if free_slots < allowed:
            allowed = free_slots

    dirs = edit.select_dirs(args.status, args.group, args.root, args.list)
    if len(dirs) == 0:
        print("No folders selected.")
        sys.exit(0)

    queued_dirs = classify.get_queued_dirs()

    # Step 1: check every folder. Nothing is submitted yet.
    ready = []
    for calc_dir in dirs:
        if not os.path.isdir(calc_dir):
            print("Not a folder, skipped: " + calc_dir)
            continue

        record = classify.classify(calc_dir, queued_dirs)

        if record["status"] == config.STATUS_RUNNING:
            print("Running, skipped: " + calc_dir)
            continue

        missing = scan.find_missing_inputs(calc_dir)
        if len(missing) > 0:
            print("Missing " + ", ".join(missing) + ", skipped: "
                  + calc_dir)
            continue

        if record["status"] == config.STATUS_CONVERGED and not args.force:
            print("Converged, skipped (use --force): " + calc_dir)
            continue

        # Warning: last electronic loop hit NELM
        if record["scf_at_nelm"]:
            print("Warning: last SCF hit NELM. Fix NELM or ALGO"
                  " first: " + calc_dir)

        # Note: the relaxation met EDIFFG before the job died
        if record["status"] == config.STATUS_RELAX_DONE_CRASHED:
            print("Note: reached required accuracy before the job"
                  " died. Fix the cause, then this should finish"
                  " quickly: " + calc_dir)

        # Warning and optional skip: ZBRENT crash near the minimum
        if record["zbrent_note"] is not None:
            print("Warning: ZBRENT: fatal error in bracketing, "
                  + record["zbrent_note"] + ": " + calc_dir)
            if args.skip_zbrent_met and record["zbrent_met"]:
                print("ZBRENT criteria met, skipped: " + calc_dir)
                continue

        # Warning: same crash as the previous run
        if record["status"] in [config.STATUS_CRASHED,
                                config.STATUS_RELAX_DONE_CRASHED]:
            old_label = history.previous_crash_label(calc_dir,
                                                     record["job_id"])
            if old_label is not None and old_label == record["message_label"]:
                print("Warning: same error as previous run ("
                      + old_label + "). Change settings first: "
                      + calc_dir)

        restart = False
        if needs_contcar_restart(calc_dir, record):
            safe, reason = check_contcar(calc_dir)
            if not safe:
                print(reason + ", skipped: " + calc_dir)
                continue
            restart = True

        ready.append((calc_dir, restart))

    if len(ready) == 0:
        print("Nothing to submit.")
        sys.exit(0)

    # Step 2: keep only as many folders as allowed
    to_submit = ready[:allowed]
    left_over = len(ready) - len(to_submit)

    print("")
    print("Folders to submit: " + str(len(to_submit)))
    for calc_dir, restart in to_submit:
        if restart:
            print("  " + calc_dir + "  (CONTCAR to POSCAR)")
        else:
            print("  " + calc_dir)
    if left_over > 0:
        print("Not submitted now because of the limits: "
              + str(left_over))

    answer = input("Type yes to save each run and submit: ")
    if answer.strip() != "yes":
        print("Cancelled. Nothing submitted.")
        sys.exit(0)

    # Step 3: save the old run, copy CONTCAR if needed, then submit
    submitted = 0
    for calc_dir, restart in to_submit:
        history.archive_one(calc_dir, queued_dirs)

        if restart:
            copy_contcar_to_poscar(calc_dir)
            print("CONTCAR copied to POSCAR: " + calc_dir)

        job_id = submit_one(calc_dir)
        if job_id is not None:
            print("Submitted job " + job_id + ": " + calc_dir)
            submitted = submitted + 1

    print("")
    print("Submitted: " + str(submitted))
    if left_over > 0:
        print("Run the same command again later for the next batch.")