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
# Example:
#   python3 agent.py status /path/to/calculations
#   python3 agent.py submit --status "not submitted" --root /path

import getpass
import os
import subprocess
import sys

import classify
import config
import scan


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


# Print how many of my jobs are running and pending.
def print_queue_summary():
    states = get_job_states()

    if states is None:
        print("Queue: squeue not available.")
        return

    total = 0
    for state in states:
        total = total + states[state]

    print("My jobs in the queue: " + str(total))
    for state in sorted(states):
        print("  " + state.lower() + ": " + str(states[state]))

    if config.QUEUE_LIMIT > 0:
        free = config.QUEUE_LIMIT - total
        if free < 0:
            free = 0
        print("  free slots under limit " + str(config.QUEUE_LIMIT)
              + ": " + str(free))


# Print how many folders are in each status.
def print_folder_summary(root):
    records = classify.classify_all(root)

    counts = {}
    for record in records:
        status = record["status"]
        counts[status] = counts.get(status, 0) + 1

    print("")
    print("Folders under " + os.path.abspath(root) + ": "
          + str(len(records)))

    # Print in report group order, so the output is always the same
    for group_name, statuses in config.REPORT_GROUPS:
        for status in statuses:
            if status in counts:
                print("  " + status + ": " + str(counts[status]))

    # Show folders that need attention
    problems = []
    for record in records:
        if record["scf_at_nelm"]:
            problems.append(record["path"] + " [SCF at NELM]")
        elif record["zbrent_met"]:
            problems.append(record["path"] + " [ZBRENT, criteria met]")

    if len(problems) > 0:
        print("")
        print("Needs a look:")
        for text in problems:
            print("  " + text)


# Run another script in this folder and pass the options on.
# Return the exit code of that script.
def run_script(script_name, options):
    code_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(code_dir, script_name)

    command = [sys.executable, script_path] + options
    result = subprocess.run(command)
    return result.returncode


def print_usage():
    print("Usage:")
    print("  python3 agent.py status <root>")
    print("  python3 agent.py report <root>")
    print("  python3 agent.py history <root>")
    print("  python3 agent.py edit [options]")
    print("  python3 agent.py submit [options]")
    print("")
    print("Options for edit and submit are the same as edit.py"
          " and resubmit.py.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]
    rest = sys.argv[2:]

    if command == "status":
        if len(rest) != 1:
            print("Usage: python3 agent.py status <root>")
            sys.exit(1)

        root = scan.resolve_path(rest[0])
        if not os.path.isdir(root):
            print("Error: not a directory: " + root)
            sys.exit(1)

        print_queue_summary()
        print_folder_summary(root)

    elif command == "report":
        sys.exit(run_script("report.py", rest))

    elif command == "history":
        sys.exit(run_script("history.py", rest))

    elif command == "edit":
        sys.exit(run_script("edit.py", rest))

    elif command == "submit":
        sys.exit(run_script("resubmit.py", rest))

    else:
        print("Unknown command: " + command)
        print("")
        print_usage()
        sys.exit(1)
