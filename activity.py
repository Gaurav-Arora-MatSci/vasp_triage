# activity.py
# Keep a record of every vtriage command in one place, so the whole
# history across machines can be read later.
#
# Off by default. It does nothing until ACTIVITY_LOG_DIR is set in
# config.py. See the README for how to set up the folder, and how to
# make it a private git repository if you want the log on every
# machine.
#
# Layout inside the log folder:
#   logs/<machine>_<year>-<month>.log   one file per machine, per month
#   MASTER.md                           all machines, current month
#   push_error.log                      why the last push failed

import datetime
import os
import signal
import subprocess
import time

import config


# Return the log folder as a full path, or None if the feature is off.
def log_dir():
    if config.ACTIVITY_LOG_DIR.strip() == "":
        return None

    path = os.path.expanduser(config.ACTIVITY_LOG_DIR)
    return os.path.abspath(path)


# Return the name of this machine, for file names and headers.
def machine_name():
    name = config.MACHINE_NAME.strip()
    if name == "":
        return "unknown"

    # Keep the name safe for a file name
    safe = ""
    for letter in name:
        if letter.isalnum() or letter in "-_":
            safe = safe + letter
        else:
            safe = safe + "_"

    return safe


# Return the current month as text, for example 2026-10.
def month_text():
    return datetime.datetime.now().strftime("%Y-%m")


# Return the log file for this machine and this month.
# The file name changes on its own when the month changes, so old
# months stay in place and nothing is ever deleted.
def current_log_path():
    folder = log_dir()
    if folder is None:
        return None

    name = machine_name() + "_" + month_text() + ".log"
    return os.path.join(folder, "logs", name)


# Make the log folder and its logs subfolder if they do not exist.
# Return True if the folder is ready.
def make_folders():
    folder = log_dir()
    if folder is None:
        return False

    logs = os.path.join(folder, "logs")
    if not os.path.isdir(logs):
        os.makedirs(logs)

    return True


# List the log files of the current month, one per machine.
# Return a list of (machine name, full path), sorted by machine.
def current_month_files():
    folder = log_dir()
    if folder is None:
        return []

    logs = os.path.join(folder, "logs")
    if not os.path.isdir(logs):
        return []

    ending = "_" + month_text() + ".log"
    found = []

    for name in sorted(os.listdir(logs)):
        if not name.endswith(ending):
            continue
        machine = name[:len(name) - len(ending)]
        found.append((machine, os.path.join(logs, name)))

    return found


# Rebuild MASTER.md from the current month of every machine.
# Older months stay in their own files under logs/.
def rebuild_master():
    folder = log_dir()
    if folder is None:
        return

    parts = []
    parts.append("# vtriage activity, " + month_text())
    parts.append("")
    parts.append("Built from the files in logs/. Older months are in"
                 " that folder too.")
    parts.append("")

    for machine, path in current_month_files():
        parts.append("")
        parts.append("#######  " + machine + "  #######")
        parts.append("")

        with open(path, "r", errors="replace") as f:
            parts.append(f.read().rstrip())

        parts.append("")

    master_path = os.path.join(folder, "MASTER.md")
    with open(master_path, "w") as f:
        f.write("\n".join(parts) + "\n")


# Remove git's lock file if it is older than
# ACTIVITY_STALE_LOCK_MINUTES. A push stopped halfway, for example by
# Slurm at the end of a job, leaves it behind, and every later push
# then fails. A real git command holds the lock for seconds only.
def clear_stale_lock(folder):
    lock_path = os.path.join(folder, ".git", "index.lock")
    if not os.path.isfile(lock_path):
        return

    age = time.time() - os.path.getmtime(lock_path)
    if age < config.ACTIVITY_STALE_LOCK_MINUTES * 60:
        return

    try:
        os.remove(lock_path)
    except OSError:
        pass


# Send the log folder to its git remote, if it is a git repository.
# On a login node this runs in the background and never blocks the
# command you ran. Inside a Slurm job it runs in the foreground, with
# a time limit, because Slurm stops background work when the job
# ends. Failures are written to push_error.log. Inside a Slurm job a
# failure also prints one line, which goes to the job log, such as
# auto_cron.log.
def push_async():
    folder = log_dir()
    if folder is None:
        return
    if not config.ACTIVITY_LOG_PUSH:
        return
    if not os.path.isdir(os.path.join(folder, ".git")):
        return

    clear_stale_lock(folder)

    error_file = os.path.join(folder, "push_error.log")

    # Commit first, then pull, then push. A pull with unstaged
    # changes in the folder is refused, and the new log entry is
    # always an unstaged change. The middle test keeps the chain
    # going when there is nothing new to commit.
    command = ("git add -A"
               " && (git diff --cached --quiet"
               " || git commit -q -m \"vtriage log from "
               + machine_name() + "\")"
               " && git pull --rebase --quiet"
               " && git push --quiet")

    # Never ask for a password. Without this, a folder set up for
    # HTTPS stops and waits for a username in the middle of
    # whatever the user is doing.
    child_env = os.environ.copy()
    child_env["GIT_TERMINAL_PROMPT"] = "0"
    child_env["GIT_ASKPASS"] = "echo"
    child_env["SSH_ASKPASS"] = "echo"

    in_slurm_job = "SLURM_JOB_ID" in os.environ

    try:
        with open(error_file, "w") as errors:
            # A new session lets a slow push be stopped as one group
            process = subprocess.Popen(command,
                                       shell=True,
                                       cwd=folder,
                                       stdin=subprocess.DEVNULL,
                                       stdout=errors,
                                       stderr=errors,
                                       env=child_env,
                                       start_new_session=True)
    except OSError:
        # Nothing to do. The log is already written on disk.
        return

    if not in_slurm_job:
        return

    # Inside a Slurm job: wait for the push before the job ends
    try:
        code = process.wait(timeout=config.ACTIVITY_PUSH_WAIT_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except OSError:
            pass
        print("Activity log: push stopped after "
              + str(config.ACTIVITY_PUSH_WAIT_SECONDS)
              + " s. It is retried on the next command.")
        return

    if code != 0:
        print("Activity log: push failed. See " + error_file)


# Add one entry to this machine's log, then rebuild MASTER.md and
# push. Does nothing when the feature is off.
def write_entry(command_text, root, result_text, output_text):
    if not make_folders():
        return

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    if root is None:
        root_text = "no root"
    else:
        root_text = root

    lines = []
    lines.append("=" * 70)
    lines.append(now + " | " + machine_name() + " | " + root_text)
    lines.append("$ vtriage " + command_text)
    lines.append("Result: " + result_text)
    lines.append("")
    lines.append(output_text.rstrip())
    lines.append("")

    path = current_log_path()
    with open(path, "a") as f:
        f.write("\n".join(lines) + "\n")

    rebuild_master()
    push_async()


# Start a fresh log for this machine and keep the old one.
# The current file is renamed with the date and time, so nothing is
# lost. Return the new name of the old file, or None.
def archive_now():
    path = current_log_path()
    if path is None or not os.path.isfile(path):
        return None

    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    new_path = path[:-4] + "_archived_" + stamp + ".log"

    number = 2
    while os.path.exists(new_path):
        new_path = (path[:-4] + "_archived_" + stamp + "_"
                    + str(number) + ".log")
        number = number + 1

    os.rename(path, new_path)
    rebuild_master()
    push_async()

    return new_path


# Return the last few entries of this machine's log as text.
# Return an empty string if there is nothing to show.
def recent_text(entries):
    path = current_log_path()
    if path is None or not os.path.isfile(path):
        return ""

    with open(path, "r", errors="replace") as f:
        text = f.read()

    # Entries are separated by a line of = signs
    blocks = text.split("=" * 70)

    kept = []
    for block in blocks:
        if block.strip() != "":
            kept.append(block.rstrip())

    if len(kept) == 0:
        return ""

    return ("=" * 70 + "\n").join(kept[-entries:])
