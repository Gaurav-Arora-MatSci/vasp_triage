# schedule.py
# Put the auto agent on scrontab, in two steps, and take it off again.
# Written for NERSC Perlmutter, where scrontab is the Slurm cron.
#
# Actions:
#   plan     show the scrontab block for a root folder and save it in
#            schedule_plan.json in that folder. Changes nothing else.
#   confirm  install the saved plan in the scrontab table, then run
#            one auto cycle at once, so the first jobs start now.
#   remove   take the block for a root folder out of the table.
#
# The table is read with scrontab -l and written back whole with
# scrontab FILE, so every other entry is kept. A copy of the old table
# is saved in the root folder before each change. If the table cannot
# be read, nothing is written.
#
# Example:
#   vtriage schedule --every 20m
#   vtriage confirm
#   vtriage unschedule

import argparse
import datetime
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time

import agent
import auto
import config
import edit
import scan


# Read and check the command line options.
def read_arguments():
    parser = argparse.ArgumentParser(
        description="Put the auto agent on scrontab or take it off.")

    parser.add_argument("action", choices=["plan", "confirm", "remove"],
                        help="plan, confirm, or remove")
    parser.add_argument("--root", default=".",
                        help="campaign root, default is this folder")
    parser.add_argument("--every", default=config.SCHEDULE_EVERY,
                        help="time between cycles, such as 20m or 5h")
    parser.add_argument("--path", action="append", nargs="+",
                        default=[],
                        help="path patterns such as C11/2, C11/*, or"
                             " C11/{2..10}; quote them in the shell")
    parser.add_argument("--batch", type=int, default=None,
                        help="new jobs per cycle, default AUTO_BATCH")
    parser.add_argument("--queue-limit", type=int, default=None,
                        help="my jobs allowed in the queue, default"
                             " AUTO_QUEUE_LIMIT")

    args = parser.parse_args()

    if args.batch is not None and args.batch < 1:
        print("Error: --batch must be 1 or more.")
        sys.exit(1)

    if args.queue_limit is not None and args.queue_limit < 0:
        print("Error: --queue-limit must be 0 or more.")
        sys.exit(1)

    return args


# Return the date and time as text, for example 2026-10-11 14:05.
def now_text():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


# Turn an interval such as 20m or 5h into a cron time.
# Return (cron text, note, error). Error is None when the interval
# is valid. Note is None unless the gaps are uneven.
def interval_to_cron(text):
    text = text.strip().lower()

    if text.endswith("min"):
        number_text = text[:-3]
        unit = "m"
    elif text.endswith("m"):
        number_text = text[:-1]
        unit = "m"
    elif text.endswith("h"):
        number_text = text[:-1]
        unit = "h"
    else:
        return None, None, ("Error: interval must end in m or h,"
                            " such as 20m or 5h.")

    try:
        number = int(number_text)
    except ValueError:
        return None, None, "Error: interval must be a whole number."

    # 60 minutes is the same as 1 hour
    if unit == "m" and number == 60:
        unit = "h"
        number = 1

    if unit == "m":
        if number < config.SCHEDULE_MIN_MINUTES or number > 59:
            return None, None, ("Error: minutes must be from "
                                + str(config.SCHEDULE_MIN_MINUTES)
                                + " to 60. For longer intervals use"
                                " whole hours, such as 2h.")
        cron = "*/" + str(number) + " * * * *"
        note = None
        if 60 % number != 0:
            note = ("Note: " + str(number) + " does not divide 60, so"
                    " the gap at the start of each hour is shorter.")
        return cron, note, None

    # Hours. Minute SCHEDULE_MINUTE avoids the busy hour mark.
    minute = str(config.SCHEDULE_MINUTE)
    if number < 1 or number > 24:
        return None, None, "Error: hours must be from 1 to 24."

    if number == 1:
        return minute + " * * * *", None, None

    if number == 24:
        return minute + " 0 * * *", None, None

    cron = minute + " */" + str(number) + " * * *"
    note = None
    if 24 % number != 0:
        note = ("Note: " + str(number) + " does not divide 24, so the"
                " gap across midnight UTC is shorter.")
    return cron, note, None


# Return the NERSC account for the scrontab job.
# SCHEDULE_ACCOUNT wins. Otherwise use the -A value in
# AUTO_EMAIL_SBATCH_OPTIONS. Return "" if neither is set.
def find_account():
    if config.SCHEDULE_ACCOUNT != "":
        return config.SCHEDULE_ACCOUNT

    options = config.AUTO_EMAIL_SBATCH_OPTIONS
    for index in range(len(options)):
        if options[index] == "-A" and index + 1 < len(options):
            return options[index + 1]

    return ""


# The comment line that marks our block in the table.
def marker_line(root):
    return "# vtriage schedule for " + root


# The text that identifies the cron line for this root.
def command_text(root):
    return "auto --root " + shlex.quote(root)


# Read the scrontab table.
# Return (list of lines, error). Error is None on success.
def read_table():
    try:
        result = subprocess.run(["scrontab", "-l"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                stdin=subprocess.DEVNULL,
                                universal_newlines=True)
    except FileNotFoundError:
        return None, "scrontab not found on this machine."

    if result.returncode != 0:
        message = result.stderr.strip()
        # An empty table is not an error
        if "no crontab" in message.lower():
            return [], None
        return None, "scrontab -l failed: " + message

    return result.stdout.splitlines(), None


# Save a copy of the table in the root folder.
# Return the path of the copy.
def save_backup(root, lines):
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(root, "scrontab_backup_" + stamp + ".txt")
    with open(backup_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return backup_path


# Write the table back with scrontab FILE.
# Return None on success, or the error text.
def write_table(lines):
    handle, temp_path = tempfile.mkstemp(prefix="vtriage_scrontab_",
                                         suffix=".txt")
    os.close(handle)

    with open(temp_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    try:
        result = subprocess.run(["scrontab", temp_path],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                stdin=subprocess.DEVNULL,
                                universal_newlines=True)
    except FileNotFoundError:
        os.remove(temp_path)
        return "scrontab not found on this machine."

    os.remove(temp_path)

    if result.returncode != 0:
        return "scrontab failed: " + result.stderr.strip()

    return None


# Return True if this line is our marker for root.
# NERSC may comment a line out, so only the end of the line is checked.
def is_marker(line, root):
    return line.strip().endswith(marker_line(root))


# Return True if this line is a cron line that runs auto for root.
# The root must be followed by a space or the end of the line, so
# /a/b does not match /a/bc.
def is_command(line, root):
    text = command_text(root)
    line = line.strip()
    return line.endswith(text) or (text + " ") in line


# Return True if the table already holds an entry for this root,
# either our marker or a cron line written by hand.
def has_entry(lines, root):
    for line in lines:
        if is_marker(line, root) or is_command(line, root):
            return True
    return False


# Return the auto options for the cron line, in a list.
def auto_options(root, args, patterns):
    options = ["--root", root]
    if args.batch is not None:
        options = options + ["--batch", str(args.batch)]
    if args.queue_limit is not None:
        options = options + ["--queue-limit", str(args.queue_limit)]
    for pattern in patterns:
        options.append("--path=" + pattern)
    return options


# Build the lines of the scrontab block.
def make_block(root, cron, account, options):
    code_dir = os.path.dirname(os.path.realpath(__file__))
    vtriage_path = os.path.join(code_dir, "vtriage")
    log_path = os.path.join(root, config.SCHEDULE_LOG_NAME)

    # Quote every word, so stars and braces reach auto.py unchanged
    words = [vtriage_path, "auto"]
    for option in options:
        words.append(shlex.quote(option))

    block = []
    block.append(marker_line(root))
    block.append("#SCRON -q " + config.SCHEDULE_QOS)
    block.append("#SCRON -A " + account)
    block.append("#SCRON -t " + config.SCHEDULE_TIME)
    block.append("#SCRON -J " + config.AUTO_HELPER_PREFIX + "auto")
    block.append("#SCRON -o " + log_path)
    block.append("#SCRON --open-mode=append")
    block.append(cron + " " + " ".join(words))
    return block


# Return the path of the plan file in the root folder.
def plan_path(root):
    return os.path.join(root, config.SCHEDULE_PLAN_NAME)


# Show the block and save it as a plan. Install nothing.
def do_plan(root, args):
    patterns = edit.flatten_patterns(args.path)

    # % ends a cron command and a space breaks the #SCRON lines
    for text in [root] + patterns:
        if "%" in text or " " in text:
            print("Error: the root and path patterns cannot contain"
                  " % or spaces: " + text)
            return 1

    cron, note, error = interval_to_cron(args.every)
    if error is not None:
        print(error)
        return 1

    account = find_account()
    if account == "":
        print("Error: no account. Set SCHEDULE_ACCOUNT in"
              " local_settings.py.")
        return 1

    if os.path.isfile(os.path.join(root, config.AUTO_DONE_NAME)):
        print("Error: AUTO_DONE exists in " + root)
        print("This campaign is finished. Delete AUTO_DONE to run"
              " it again.")
        return 1

    records = auto.select_records(root, patterns)
    if len(records) == 0:
        print("Error: no calculation folders match. Check --root and"
              " --path.")
        return 1

    lines, error = read_table()
    if error is not None:
        print("Error: " + error)
        return 1

    if has_entry(lines, root):
        print("Error: the scrontab table already has an entry for "
              + root)
        print("Remove it first with: vtriage unschedule --root " + root)
        return 1

    counts = auto.count_statuses(records)
    options = auto_options(root, args, patterns)
    block = make_block(root, cron, account, options)

    batch = config.AUTO_BATCH
    if args.batch is not None:
        batch = args.batch
    limit = config.AUTO_QUEUE_LIMIT
    if args.queue_limit is not None:
        limit = args.queue_limit

    print("Schedule plan for " + root)
    print("  folders: " + str(len(records))
          + ", not submitted: "
          + str(counts.get(config.STATUS_NOT_SUBMITTED, 0))
          + ", in queue: "
          + str(counts.get(config.STATUS_RUNNING, 0)))
    print("  every " + args.every + ": " + cron + " (times are UTC)")
    if note is not None:
        print("  " + note)
    print("  new jobs per cycle: " + str(batch)
          + ", queue limit: " + str(limit))
    if len(patterns) == 0:
        print("  path patterns: none, every folder")
    else:
        print("  path patterns: " + " ".join(patterns))
    if config.AUTO_EMAIL == "":
        print("  email: none, AUTO_EMAIL is empty")
    else:
        print("  email when done: " + config.AUTO_EMAIL)
    print("")
    print("Block to add to the scrontab table:")
    for line in block:
        print("  " + line)
    print("")

    plan = {"root": root,
            "created": time.time(),
            "block": block,
            "auto_options": options}
    with open(plan_path(root), "w") as f:
        json.dump(plan, f, indent=2)

    print("Nothing installed yet. Plan saved to " + plan_path(root))
    print("On confirm, the block is installed and one cycle runs at"
          " once.")
    print("To confirm, run:")
    print("  vtriage confirm --root " + root)
    return 0


# Install the saved plan, then run one auto cycle at once.
def do_confirm(root):
    path = plan_path(root)
    if not os.path.isfile(path):
        print("Error: no plan in " + root)
        print("Make one first with: vtriage schedule --root " + root)
        return 1

    with open(path) as f:
        plan = json.load(f)

    if plan["root"] != root:
        print("Error: the plan is for " + plan["root"] + ", not " + root)
        return 1

    age = time.time() - plan["created"]
    if age > config.SCHEDULE_PLAN_MINUTES * 60:
        print("Error: the plan is older than "
              + str(config.SCHEDULE_PLAN_MINUTES) + " minutes.")
        print("Make a new one with: vtriage schedule --root " + root)
        return 1

    if os.path.isfile(os.path.join(root, config.AUTO_DONE_NAME)):
        print("Error: AUTO_DONE exists in " + root
              + ". Nothing installed.")
        return 1

    lines, error = read_table()
    if error is not None:
        print("Error: " + error + " Nothing installed.")
        return 1

    if has_entry(lines, root):
        print("Error: the scrontab table already has an entry for "
              + root + ". Nothing installed.")
        return 1

    backup_path = save_backup(root, lines)

    new_lines = list(lines)
    if len(new_lines) > 0 and new_lines[-1].strip() != "":
        new_lines.append("")
    new_lines = new_lines + plan["block"]

    error = write_table(new_lines)
    if error is not None:
        print("Error: " + error + " Nothing installed.")
        return 1

    # Check that the entry is really there
    check_lines, error = read_table()
    if error is not None or not has_entry(check_lines, root):
        print("Error: the entry is not in scrontab -l after install.")
        print("The old table is saved in " + backup_path)
        return 1

    os.remove(path)

    print("Installed in the scrontab table:")
    for line in plan["block"]:
        print("  " + line)
    print("Old table saved in " + backup_path)
    print("")
    print("Running the first cycle now.")
    agent.run_script("auto.py", plan["auto_options"])

    print("")
    print("Check with: scrontab -l and squeue -u $USER")
    print("Watch with: tail -f "
          + os.path.join(root, config.SCHEDULE_LOG_NAME))
    print("The entry removes itself after the email is sent.")
    return 0


# Take the block for this root out of the table.
# Return one line of text that says what happened. Never asks for
# input and never stops with an error, so auto.py can call it.
def remove_entry(root):
    lines, error = read_table()
    if error is not None:
        return "Schedule: not removed, " + error

    start = None
    for index in range(len(lines)):
        if is_marker(lines[index], root):
            start = index
            break

    if start is None:
        return "Schedule: no vtriage entry for this root in scrontab."

    # The block ends at the cron line, a few lines below the marker.
    # NERSC may comment lines out, so search the text, not the start.
    end = None
    last = start + 10
    if last > len(lines):
        last = len(lines)
    for index in range(start + 1, last):
        if is_command(lines[index], root):
            end = index
            break

    if end is None:
        return ("Schedule: not removed, the cron line below the marker"
                " was not found. Edit with scrontab -e.")

    backup_path = save_backup(root, lines)
    new_lines = lines[:start] + lines[end + 1:]

    # Drop the blank line that was added before the block
    if start > 0 and start <= len(new_lines):
        if new_lines[start - 1].strip() == "":
            new_lines = new_lines[:start - 1] + new_lines[start:]

    error = write_table(new_lines)
    if error is not None:
        return "Schedule: not removed, " + error

    return ("Schedule: entry removed from scrontab. Old table saved in "
            + backup_path)


if __name__ == "__main__":
    args = read_arguments()

    root = os.path.abspath(scan.resolve_path(args.root))
    if not os.path.isdir(root):
        print("Error: not a directory: " + root)
        sys.exit(1)

    if args.action == "plan":
        sys.exit(do_plan(root, args))

    if args.action == "confirm":
        sys.exit(do_confirm(root))

    if args.action == "remove":
        print(remove_entry(root))
        sys.exit(0)
