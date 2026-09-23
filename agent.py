# agent.py
# One entry point for the vasp_triage tools.
#
# Commands:
#   status    short summary of my jobs and folder states
#   report    write CSV files and report.md, calls report.py
#   history   archive finished runs, calls history.py
#   edit      change INCAR and KPOINTS, calls edit.py
#   submit    submit folders with sbatch, calls resubmit.py
#
# Every command is written to agent_log.txt in the root folder,
# together with the output it printed.
#
# A folder is optional. Without one, the folder you are standing in
# is used. See the vtriage script for a short command name.
#
# Example:
#   vtriage status
#   vtriage submit --status "not submitted" --root /path

import datetime
import getpass
import os
import subprocess
import sys

import classify
import config
import scan


# Name of the command log. It is kept in the root folder.
LOG_FILE = "agent_log.txt"


# Find the root folder in the options the user typed.
# Looks for --root, then for a single plain word after the command.
# Return None if no root was given, for example with --list.
def find_root(command, rest):
    for index in range(len(rest)):
        if rest[index] == "--root" and index + 1 < len(rest):
            return scan.resolve_path(rest[index + 1])

    # status, report, history, and menu take a plain path
    if command in ["status", "report", "history", "menu"]:
        if len(rest) == 1:
            return scan.resolve_path(rest[0])
        if len(rest) == 0:
            return os.getcwd()

    # edit and submit with --list work on a file, not a root folder
    for option in rest:
        if option == "--list":
            return None

    # Nothing was given, so use the folder I am standing in
    return os.getcwd()


# Add one block to the command log in the root folder.
# If no root is known, the log goes next to the scripts instead.
def write_log(root, command_text, result_text, output_text):
    if root is not None and os.path.isdir(root):
        log_dir = root
    else:
        log_dir = os.path.dirname(os.path.abspath(__file__))

    log_path = os.path.join(log_dir, LOG_FILE)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append("=" * 70)
    lines.append(now + " | python3 agent.py " + command_text)
    lines.append("Result: " + result_text)
    lines.append("")
    lines.append(output_text.rstrip())
    lines.append("")

    with open(log_path, "a") as f:
        f.write("\n".join(lines) + "\n")


# Ask SLURM for the state of each of my jobs.
# Return a dictionary such as {"RUNNING": 3, "PENDING": 12}.
# Return None if squeue cannot be used.
def get_job_states():
    user = getpass.getuser()
    command = ["squeue", "-u", user, "-h", "-o", "%T"]

    try:
        result = subprocess.run(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
    except FileNotFoundError:
        return None

    if result.returncode != 0:
        return None

    states = {}
    for line in result.stdout.splitlines():
        state = line.strip()
        if state == "":
            continue
        states[state] = states.get(state, 0) + 1

    return states


# Build the text of the queue summary.
# Return it as one block of text instead of printing it.
def queue_summary_text():
    states = get_job_states()
    lines = []

    if states is None:
        return "Queue: squeue not available."

    total = 0
    for state in states:
        total = total + states[state]

    lines.append("My jobs in the queue: " + str(total))
    for state in sorted(states):
        lines.append("  " + state.lower() + ": " + str(states[state]))

    if config.QUEUE_LIMIT > 0:
        free = config.QUEUE_LIMIT - total
        if free < 0:
            free = 0
        lines.append("  free slots under limit "
                     + str(config.QUEUE_LIMIT) + ": " + str(free))

    return "\n".join(lines)


# Build the text of the folder summary.
def folder_summary_text(root):
    records = classify.classify_all(root)

    counts = {}
    for record in records:
        status = record["status"]
        counts[status] = counts.get(status, 0) + 1

    lines = []
    lines.append("")
    lines.append("Folders under " + os.path.abspath(root) + ": "
                 + str(len(records)))

    # Print in report group order, so the output is always the same
    for group_name, statuses in config.REPORT_GROUPS:
        for status in statuses:
            if status in counts:
                lines.append("  " + status + ": " + str(counts[status]))

    # Show folders that need attention
    problems = []
    for record in records:
        if record["scf_at_nelm"]:
            problems.append(record["path"] + " [SCF at NELM]")
        elif record["zbrent_met"]:
            problems.append(record["path"] + " [ZBRENT, criteria met]")

    if len(problems) > 0:
        lines.append("")
        lines.append("Needs a look:")
        for text in problems:
            lines.append("  " + text)

    return "\n".join(lines)


# Run another script, show its output live, and keep a copy.
# Questions from the script still work, because its input stays
# connected to the keyboard.
# Return (exit code, output text).
def run_script(script_name, options):
    code_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(code_dir, script_name)

    command = [sys.executable, script_path] + options

    # Ask Python not to hold back output, so questions appear at once
    child_env = os.environ.copy()
    child_env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               env=child_env)

    collected = []

    # Read small pieces, so a question without a newline is shown too
    while True:
        piece = process.stdout.read(1)
        if piece == b"":
            break
        text = piece.decode("utf-8", errors="replace")
        sys.stdout.write(text)
        sys.stdout.flush()
        collected.append(text)

    process.wait()
    return process.returncode, "".join(collected)


def print_usage():
    print("Usage:")
    print("  vtriage status [root]")
    print("  vtriage report [root]")
    print("  vtriage history [root]")
    print("  vtriage menu [root]")
    print("  vtriage edit [options]")
    print("  vtriage submit [options]")
    print("")
    print("Without a root, the folder you are standing in is used.")
    print("Options for edit and submit are the same as edit.py"
          " and resubmit.py.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]
    rest = sys.argv[2:]

    # The command as typed, and the root folder for the log
    command_text = " ".join(sys.argv[1:])
    root = find_root(command, rest)

    if command == "status":
        if len(rest) > 1:
            print("Usage: vtriage status [root]")
            sys.exit(1)

        if root is None or not os.path.isdir(root):
            print("Error: not a directory: " + str(root))
            sys.exit(1)

        output = queue_summary_text() + "\n" + folder_summary_text(root)
        print(output)
        write_log(root, command_text, "checked", output)

    elif command == "menu":
        import menu

        if len(rest) > 1:
            print("Usage: vtriage menu [root]")
            sys.exit(1)

        if root is None or not os.path.isdir(root):
            print("Error: not a directory: " + str(root))
            sys.exit(1)

        menu.main(os.path.abspath(root))

    elif command in ["report", "history", "edit", "submit"]:
        script_names = {"report": "report.py",
                        "history": "history.py",
                        "edit": "edit.py",
                        "submit": "resubmit.py"}

        # Pass the current folder on when no folder was given
        if command in ["report", "history"] and len(rest) == 0:
            rest = ["."]

        if command in ["edit", "submit"]:
            has_target = False
            for option in rest:
                if option in ["--root", "--list"]:
                    has_target = True
            if not has_target:
                rest = rest + ["--root", "."]

        code, output = run_script(script_names[command], rest)

        if code == 0:
            result = "finished"
        else:
            result = "failed, exit code " + str(code)

        write_log(root, command_text, result, output)
        sys.exit(code)

    else:
        print("Unknown command: " + command)
        print("")
        print_usage()
        sys.exit(1)