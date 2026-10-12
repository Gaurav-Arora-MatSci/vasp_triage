# auto.py
# One cycle of the auto agent. Run it on a schedule, such as scrontab.
#
# Each run:
#   1. stops at once if AUTO_DONE exists in the root folder
#   2. stops at once if another run holds the lock
#   3. submits not submitted folders, up to the batch size and the
#      free slots in the queue
#   4. when nothing is left to submit and no folder is in the queue,
#      writes the final report, writes AUTO_DONE with the folders that
#      need a look, and sends one email through a one minute Slurm job
##   5. after the email, takes its own entry out of scrontab, if
#      vtriage schedule put one there
#
# Only folders with status not submitted are ever submitted.
# Crashed or unconverged folders are listed, never resubmitted.
# A log entry is written only when the run submits or finishes, so a
# run every few minutes does not fill agent_log.txt.
#
# Example:
#   vtriage auto --root /path/to/campaign --path "C11/*"

import argparse
import datetime
import getpass
import os
import subprocess
import sys
import time

import agent
import classify
import config
import edit
import scan


# Read and check the command line options.
def read_arguments():
    parser = argparse.ArgumentParser(
        description="One cycle of the auto agent.")

    parser.add_argument("--root", default=".",
                        help="campaign root, default is this folder")
    parser.add_argument("--path", action="append", nargs="+",
                        default=[],
                        help="path patterns such as C11/2, C11/*, or"
                             " C11/{2..10}; quote them in the shell")
    parser.add_argument("--batch", type=int, default=config.AUTO_BATCH,
                        help="new jobs per run")
    parser.add_argument("--queue-limit", type=int,
                        default=config.AUTO_QUEUE_LIMIT,
                        help="my jobs allowed in the queue, 0 turns it"
                             " off")

    args = parser.parse_args()

    if args.batch < 1:
        print("Error: --batch must be 1 or more.")
        sys.exit(1)

    if args.queue_limit < 0:
        print("Error: --queue-limit must be 0 or more.")
        sys.exit(1)

    return args


# Return the date and time as text, for example 2026-10-11 14:05.
def now_text():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


# Create the lock file in the root folder.
# Return True if this run holds the lock, False if another run does.
# A lock older than AUTO_LOCK_MINUTES is left over from a killed run
# and is replaced.
def take_lock(root):
    lock_path = os.path.join(root, config.AUTO_LOCK_NAME)

    if os.path.isfile(lock_path):
        age = time.time() - os.path.getmtime(lock_path)
        if age < config.AUTO_LOCK_MINUTES * 60:
            return False
        print("Old lock replaced: " + lock_path)
        try:
            os.remove(lock_path)
        except OSError:
            return False

    # O_EXCL makes the creation fail if another run made it first
    try:
        handle = os.open(lock_path,
                         os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except OSError:
        return False

    os.write(handle, (now_text() + " pid " + str(os.getpid())
                      + "\n").encode("utf-8"))
    os.close(handle)
    return True


# Remove the lock file.
def release_lock(root):
    lock_path = os.path.join(root, config.AUTO_LOCK_NAME)
    try:
        os.remove(lock_path)
    except OSError:
        pass


# Count my jobs in the queue, running and pending.
# Helper jobs, named with AUTO_HELPER_PREFIX, are not counted.
# Return None if squeue cannot be used.
def count_my_jobs():
    user = getpass.getuser()
    command = ["squeue", "-u", user, "-h", "-o", "%j"]

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
        name = line.strip()
        if name == "":
            continue
        if name.startswith(config.AUTO_HELPER_PREFIX):
            continue
        count = count + 1

    return count


# Classify every folder under root and keep those that match the
# path patterns. With no patterns, every folder is kept.
def select_records(root, patterns):
    records = classify.classify_all(root)
    if len(patterns) == 0:
        return records

    expanded = edit.expand_all(patterns)
    kept = []
    for record in records:
        if edit.matches_any(record["path"], expanded):
            kept.append(record)
    return kept


# Count how many records have each status.
def count_statuses(records):
    counts = {}
    for record in records:
        status = record["status"]
        counts[status] = counts.get(status, 0) + 1
    return counts


# Submit up to count not submitted folders through resubmit.py.
# Return the text resubmit.py printed.
def submit_batch(root, patterns, count):
    options = ["--status", config.STATUS_NOT_SUBMITTED,
               "--root", root,
               "--max", str(count),
               "--queue-limit", "0",
               "--yes"]
    for pattern in patterns:
        options.append("--path=" + pattern)

    code, output = agent.run_script("resubmit.py", options)
    return output


# Build the text of AUTO_DONE.
# Return (text, number converged, number that need a look).
def make_done_text(root, patterns, records):
    counts = count_statuses(records)

    lines = []
    lines.append("vasp_triage auto agent finished")
    lines.append("Date: " + now_text())
    lines.append("Root: " + root)
    if len(patterns) == 0:
        lines.append("Path patterns: none, every folder")
    else:
        lines.append("Path patterns: " + " ".join(patterns))
    lines.append("")
    lines.append("Folders: " + str(len(records)))

    # Same order as the report
    for group_name, statuses in config.REPORT_GROUPS:
        for status in statuses:
            if status in counts:
                lines.append("  " + status + ": " + str(counts[status]))

    look = []
    for record in records:
        if record["status"] == config.STATUS_CONVERGED:
            continue

        text = record["status"] + " | " + record["path"]
        if record["message_label"] is not None:
            text = text + " | " + record["message_label"]
        if record["scf_at_nelm"]:
            text = text + " | last SCF hit NELM"
        if len(record["missing"]) > 0:
            text = text + " | missing " + ", ".join(record["missing"])
        look.append(text)

    lines.append("")
    lines.append("Folders that need a look: " + str(len(look)))
    for text in look:
        lines.append("  " + text)

    converged = counts.get(config.STATUS_CONVERGED, 0)
    return "\n".join(lines) + "\n", converged, len(look)


# Keep letters, digits, _ and - so the text is safe in a job name.
def safe_name(text):
    kept = ""
    for letter in text:
        if letter.isalnum() or letter in "_-":
            kept = kept + letter
        else:
            kept = kept + "_"
    return kept


# Submit a one minute job that only prints AUTO_DONE.
# Slurm sends the email when it ends. The job name carries the counts,
# so they show in the subject line.
# Return a line of text that says what happened.
def send_email(root, converged, look):
    if config.AUTO_EMAIL == "":
        return "Email: not sent, AUTO_EMAIL is empty."

    name = (config.AUTO_HELPER_PREFIX + "done_"
            + safe_name(os.path.basename(root)) + "_"
            + str(converged) + "ok_" + str(look) + "look")

    command = (["sbatch"] + config.AUTO_EMAIL_SBATCH_OPTIONS
               + ["-J", name,
                  "-o", "vtriage_done.out",
                  "--mail-type=END",
                  "--mail-user=" + config.AUTO_EMAIL,
                  "--wrap=cat " + config.AUTO_DONE_NAME])

    try:
        result = subprocess.run(command,
                                cwd=root,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
    except FileNotFoundError:
        return "Email: not sent, sbatch not found."

    if result.returncode != 0:
        return "Email: not sent, sbatch failed: " + result.stderr.strip()

    return ("Email: " + result.stdout.strip() + ", to "
            + config.AUTO_EMAIL)


# Write the final report, AUTO_DONE, and the email.
def finish(root, patterns, records):
    print("Nothing left to submit and nothing in the queue.")
    print("Writing the final report.")
    agent.run_script("report.py", [root])

    text, converged, look = make_done_text(root, patterns, records)

    # AUTO_DONE is written before the email job, which prints it
    done_path = os.path.join(root, config.AUTO_DONE_NAME)
    with open(done_path, "w") as f:
        f.write(text)

    email_line = send_email(root, converged, look)
    with open(done_path, "a") as f:
        f.write("\n" + email_line + "\n")

    print(text)
    print(email_line)
    agent.write_log(root, "auto finish", "campaign done",
                    text + "\n" + email_line)

    # Last step, because removing the entry may end this scrontab job.
    # schedule.py imports this file, so it is imported here.
    import schedule
    schedule_line = schedule.remove_entry(root)
    with open(done_path, "a") as f:
        f.write(schedule_line + "\n")
    print(schedule_line)


# Run one cycle. Return the exit code.
def run_cycle(root, patterns, args):
    stamp = now_text()

    records = select_records(root, patterns)
    if len(records) == 0:
        print(stamp + " Error: no calculation folders match."
              " Check --root and --path.")
        return 1

    counts = count_statuses(records)
    waiting = counts.get(config.STATUS_NOT_SUBMITTED, 0)
    queued = counts.get(config.STATUS_RUNNING, 0)

    summary = (stamp + " folders: " + str(len(records))
               + ", not submitted: " + str(waiting)
               + ", in queue: " + str(queued))
    print(summary)

    # Step 1: fill the free slots with new jobs
    if waiting > 0:
        my_jobs = count_my_jobs()
        if my_jobs is None:
            print("squeue failed. Nothing submitted.")
            return 1

        allowed = args.batch
        if args.queue_limit > 0:
            free = args.queue_limit - my_jobs
            if free < allowed:
                allowed = free

        if allowed <= 0:
            print("Queue full: " + str(my_jobs) + " of "
                  + str(args.queue_limit) + ". Nothing submitted.")
            return 0

        output = submit_batch(root, patterns, allowed)
        agent.write_log(root, "auto submit",
                        "up to " + str(allowed) + " jobs",
                        summary + "\n" + output)
        return 0

    # Step 2: everything was submitted, wait for the queue to empty
    if queued > 0:
        print("All submitted. Waiting for " + str(queued)
              + " jobs to leave the queue.")
        return 0

    # Step 3: done
    finish(root, patterns, records)
    return 0


if __name__ == "__main__":
    args = read_arguments()

    root = os.path.abspath(scan.resolve_path(args.root))
    if not os.path.isdir(root):
        print("Error: not a directory: " + root)
        sys.exit(1)

    patterns = edit.flatten_patterns(args.path)

    done_path = os.path.join(root, config.AUTO_DONE_NAME)
    if os.path.isfile(done_path):
        print(now_text() + " AUTO_DONE found, nothing to do: " + root)
        sys.exit(0)

    if not take_lock(root):
        print(now_text() + " Another auto run is active. Skipped.")
        sys.exit(0)

    try:
        code = run_cycle(root, patterns, args)
    finally:
        release_lock(root)

    sys.exit(code)
