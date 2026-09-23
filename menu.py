# menu.py
# A numbered menu for the vasp_triage tools.
# It only builds commands and hands them to agent.py, so every
# option here also works on the command line.
#
# Start it with:  vtriage menu
# or with:        python3 menu.py [root]

import os
import sys

import agent
import config
import scan


# Ask a question and return the answer with spaces removed.
def ask(question):
    try:
        return input(question).strip()
    except EOFError:
        return ""


# Show numbered choices and return the one the user picked.
# choices is a list of (label, value).
# Return None if the user pressed 0 or entered nothing.
def ask_choice(title, choices):
    print("")
    print(title)
    number = 1
    for label, value in choices:
        print("  " + str(number) + ") " + label)
        number = number + 1
    print("  0) back")

    answer = ask("Choice: ")
    if not answer.isdigit():
        return None

    index = int(answer)
    if index < 1 or index > len(choices):
        return None

    return choices[index - 1][1]


# Ask for a value until the user types something, or gives up.
def ask_text(question):
    while True:
        answer = ask(question)
        if answer != "":
            return answer
        print("Nothing entered. Press 0 to go back.")
        if ask("Press Enter to try again, or 0 to go back: ") == "0":
            return None


# Build the list of options that choose folders.
# Return a list such as ["--status", "crashed"], or None.
def ask_selection(root):
    groups = []
    for group_name, statuses in config.REPORT_GROUPS:
        groups.append(("group: " + group_name, group_name))

    statuses = []
    for group_name, group_statuses in config.REPORT_GROUPS:
        for status in group_statuses:
            statuses.append(("status: " + status, status))

    choices = groups + statuses + [("from a list file", "list")]

    picked = ask_choice("Which folders?", choices)
    if picked is None:
        return None

    if picked == "list":
        list_path = ask_text("Path of the list file: ")
        if list_path is None:
            return None
        return ["--list", list_path]

    # A group name is one word, a status can hold spaces
    for group_name, group_statuses in config.REPORT_GROUPS:
        if picked == group_name:
            return ["--group", picked, "--root", root]

    return ["--status", picked, "--root", root]


# Ask for the options of the edit command.
# Return the full option list, or None.
def ask_edit_options(root):
    options = ask_selection(root)
    if options is None:
        return None

    changes = []

    while True:
        choices = [("set a tag, for example NELM=200", "set"),
                   ("remove a tag", "remove"),
                   ("rewrite KPOINTS", "kpoints"),
                   ("only folders where a tag has a value", "where"),
                   ("done, show me the preview", "done")]

        picked = ask_choice("What should be changed?", choices)
        if picked is None:
            return None

        if picked == "done":
            break

        if picked == "set":
            tag = ask_text("Tag name, for example EDIFF: ")
            if tag is None:
                continue
            value = ask_text("New value for " + tag.upper() + ": ")
            if value is None:
                continue
            changes = changes + ["--set", tag.upper() + "=" + value]

        elif picked == "remove":
            tag = ask_text("Tag to delete: ")
            if tag is None:
                continue
            changes = changes + ["--remove", tag.upper()]

        elif picked == "kpoints":
            scheme = ask_choice("KPOINTS scheme?",
                                [("Gamma centred", "gamma"),
                                 ("Monkhorst Pack", "mp")])
            if scheme is None:
                continue
            mesh = ask_text("Mesh, three numbers such as 4 4 4: ")
            if mesh is None:
                continue
            numbers = mesh.split()
            if len(numbers) != 3:
                print("Give exactly three numbers.")
                continue
            changes = changes + ["--kpoints", scheme] + numbers

        elif picked == "where":
            tag = ask_text("Tag to match, for example ALGO: ")
            if tag is None:
                continue
            value = ask_text("Value it must have: ")
            if value is None:
                continue
            changes = changes + ["--where", tag.upper() + "=" + value]

        print("So far: " + " ".join(changes))

    if len(changes) == 0:
        print("No change chosen.")
        return None

    return options + changes


# Ask for the extra options of the submit command.
# Return the full option list, or None.
def ask_submit_options(root):
    options = ask_selection(root)
    if options is None:
        return None

    while True:
        choices = [("submit now", "done"),
                   ("set the number of jobs per run", "max"),
                   ("set the queue limit", "queue"),
                   ("also submit converged folders", "force"),
                   ("skip ZBRENT folders that look relaxed", "zbrent")]

        picked = ask_choice("Anything else?", choices)
        if picked is None:
            return None

        if picked == "done":
            break

        if picked == "max":
            value = ask_text("Largest number of jobs per run: ")
            if value is None or not value.isdigit():
                print("Give a whole number.")
                continue
            options = options + ["--max", value]

        elif picked == "queue":
            value = ask_text("Jobs allowed in the queue, 0 for no"
                             " limit: ")
            if value is None or not value.isdigit():
                print("Give a whole number.")
                continue
            options = options + ["--queue-limit", value]

        elif picked == "force":
            options = options + ["--force"]

        elif picked == "zbrent":
            options = options + ["--skip-zbrent-met"]

        print("So far: " + " ".join(options))

    return options


# Show the command, then run it through agent.py.
def run_command(command, options):
    text = "vtriage " + command + " " + " ".join(options)
    print("")
    print("Running: " + text.strip())
    print("")

    script_names = {"report": "report.py",
                    "history": "history.py",
                    "edit": "edit.py",
                    "submit": "resubmit.py"}

    code, output = agent.run_script(script_names[command], options)

    root = agent.find_root(command, options)
    if code == 0:
        result = "finished"
    else:
        result = "failed, exit code " + str(code)

    agent.write_log(root, command + " " + " ".join(options),
                    result, output)


# Print the status summary and write it to the log.
def show_status(root):
    output = (agent.queue_summary_text() + "\n"
              + agent.folder_summary_text(root))
    print("")
    print(output)
    agent.write_log(root, "status " + root, "checked", output)


# Ask for a new root folder. Return the old one if nothing is given.
def ask_root(old_root):
    answer = ask("New root folder, or a short name: ")
    if answer == "":
        return old_root

    new_root = scan.resolve_path(answer)
    if not os.path.isdir(new_root):
        print("Not a directory: " + new_root)
        return old_root

    return os.path.abspath(new_root)


def main(root):
    while True:
        print("")
        print("=" * 60)
        print("vasp_triage")
        print("Root: " + root)

        choices = [("status summary", "status"),
                   ("write report", "report"),
                   ("archive finished runs", "history"),
                   ("submit jobs", "submit"),
                   ("edit INCAR or KPOINTS", "edit"),
                   ("change the root folder", "root")]

        picked = ask_choice("What would you like to do?", choices)

        if picked is None:
            print("Bye.")
            return

        if picked == "status":
            show_status(root)

        elif picked == "root":
            root = ask_root(root)

        elif picked in ["report", "history"]:
            run_command(picked, [root])

        elif picked == "submit":
            options = ask_submit_options(root)
            if options is not None:
                run_command("submit", options)

        elif picked == "edit":
            options = ask_edit_options(root)
            if options is not None:
                run_command("edit", options)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        print("Usage: python3 menu.py [root]")
        sys.exit(1)

    if len(sys.argv) == 2:
        start_root = scan.resolve_path(sys.argv[1])
    else:
        start_root = os.getcwd()

    if not os.path.isdir(start_root):
        print("Error: not a directory: " + start_root)
        sys.exit(1)

    main(os.path.abspath(start_root))
