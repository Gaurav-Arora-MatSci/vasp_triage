# resubmit.py
# Submit selected calculation folders with sbatch.
# Saves each old run with history.py before submitting.
# Submits at most MAX_SUBMIT jobs per run, unless --max is given.

import argparse
import os
import subprocess
import sys

import classify
import config
import edit
import history
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
                        help="largest number of jobs to submit")
    parser.add_argument("--force", action="store_true",
                        help="also submit converged folders")

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

    return args


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

        ready.append(calc_dir)

    if len(ready) == 0:
        print("Nothing to submit.")
        sys.exit(0)

    # Step 2: keep only the first --max folders
    to_submit = ready[:args.max]
    left_over = len(ready) - len(to_submit)

    print("")
    print("Folders to submit: " + str(len(to_submit)))
    for calc_dir in to_submit:
        print("  " + calc_dir)
    if left_over > 0:
        print("Not submitted now because of --max: " + str(left_over))

    answer = input("Type yes to save each run and submit: ")
    if answer.strip() != "yes":
        print("Cancelled. Nothing submitted.")
        sys.exit(0)

    # Step 3: save the old run, then submit
    submitted = 0
    for calc_dir in to_submit:
        history.archive_one(calc_dir, queued_dirs)

        job_id = submit_one(calc_dir)
        if job_id is not None:
            print("Submitted job " + job_id + ": " + calc_dir)
            submitted = submitted + 1

    print("")
    print("Submitted: " + str(submitted))
    if left_over > 0:
        print("Run the same command again later for the next batch.")
