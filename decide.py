# decide.py
# The decision agent. It continues finished calculations that did not
# converge, within fixed limits, and asks you about everything else.
#
# It is off unless AGENT_MODE is set in local_settings.py, or
# vtriage auto gets --agent for one campaign:
#   off   nothing happens (default)
#   ask   every action goes into agent_plan.json and waits for
#         vtriage approve
#   auto  allowed actions are applied and submitted at once
#
# Allowed actions, and nothing else:
#   ionic not converged, still improving  -> CONTCAR to POSCAR, resubmit
#   walltime hit in a relaxation          -> CONTCAR to POSCAR, resubmit
#   SCF not converged, still improving    -> raise NELM, rerun once
# A relaxation means IBRION 1, 2, or 3. MD and finite difference runs
# are never restarted.
# At most 3 runs per relaxation and 2 per SCF case, counting the first.
# The count starts again after you resubmit a folder yourself.
# A submit that sbatch refuses is tried again, at most
# AGENT_SUBMIT_TRIES times, with the files put back in between.
# Everything else waits for you.
#
# The LLM only judges whether a run is still improving. It has no
# tools: this file collects the numbers, puts them in the prompt, and
# checks every answer against the rules before acting. The LLM never
# reads or writes a file.
#
# Files this agent writes in the root folder:
#   agent_state.json   decisions per folder and the money spent
#   agent_plan.json    actions waiting for vtriage approve (ask mode)
#   agent_summary.txt  plain English summary of the latest cycle
#
# Example:
#   vtriage approve --root /path/to/campaign

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

import agent
import classify
import config
import edit
import evidence
import history
import parse
import resubmit
import scan


MODES = ["off", "ask", "auto"]

# Lines the agent writes to progress.txt after each submitted job, so
# the history of the folder shows what the agent did and why.
PROGRESS_RESTART = "Agent: restart from CONTCAR"
PROGRESS_NELM = "Agent: NELM"

# IBRION values of an ionic relaxation. Others, such as 0 for MD or 5
# to 8 for finite differences, are never restarted.
RELAX_IBRION = [1, 2, 3]

# Kinds of case. llm kinds are judged by the LLM, the rest by rules.
KIND_DONE = "done"
KIND_WAIT = "wait"
KIND_SKIP = "skip"
KIND_RESTART = "restart"
KIND_LLM_IONIC = "llm ionic"
KIND_LLM_SCF = "llm scf"

# Group titles in the summary, in the order they are shown
GROUP_RESTARTED = "Restarted from CONTCAR"
GROUP_RERUN = "NELM raised and rerun"
GROUP_PLANNED = "Planned, waiting for vtriage approve"
GROUP_RETRY = "Submit refused, tried again next cycle"
GROUP_WAIT = "Waiting for you"
GROUP_FAILED = "Submit failed, waiting for you"
GROUP_SKIP = "Skipped, check CONTCAR"
GROUP_DONE = "Done, reached required accuracy before the job died"
GROUP_TITLES = [GROUP_RESTARTED, GROUP_RERUN, GROUP_PLANNED, GROUP_RETRY,
                GROUP_WAIT, GROUP_FAILED, GROUP_SKIP, GROUP_DONE]

# Error label for a job stopped by the time limit, as in
# config.ERROR_PATTERNS (DUE TO TIME LIMIT)
WALLTIME_LABEL = "walltime"

# Instructions for the LLM. It replaces the default system prompt, so
# the LLM sees nothing else about this machine.
SYSTEM_PROMPT = """\
You review unfinished VASP calculations for an automated job manager.
You cannot run commands or read files. All data is in the message.
For each folder, choose one decision from its allowed list, based on the
trend in the numbers.

Folders of kind ionic: the relaxation used all NSW steps, or the job hit
its time limit, before reaching EDIFFG.
- Choose restart only if the relaxation is still making steady progress:
  the energy keeps going down without sustained oscillation, and the max
  force is generally falling toward the EDIFFG limit.
- Choose wait if the energy oscillates, rises, or has flattened while
  forces stay far above the limit, if forces are not falling, if
  electronic steps per ionic step are growing toward NELM, or if the
  data is unclear.

Folders of kind scf: the last electronic loop used all NELM steps
without reaching EDIFF.
- Choose rerun only if dE falls steadily toward EDIFF, so that more
  steps will likely converge it. Give nelm, the new NELM, larger than
  the current value and not above the largest value allowed. Estimate it
  from the rate at which dE falls, with some margin.
- Each step is marked fixed density or density updated. In the fixed
  density steps at the start, VASP holds the charge density fixed, so
  their dE says nothing about convergence. A jump in dE at the first
  density update, or where the method switches, such as DAV to RMM, is
  normal. Judge the trend only from the density updated steps after
  any switch.
- Choose wait if dE oscillates, stalls, or grows in those steps, or if
  the loop looks like charge sloshing that needs other settings.

When unsure, choose wait. A person checks every wait case, so wait is
always safe.
reason: one plain English sentence of at most 30 words that cites the
key numbers.

Reply with only one JSON object and no other text, in this form:
{"decisions": [
 {"id": "F1", "decision": "restart", "reason": "..."},
 {"id": "F2", "decision": "rerun", "nelm": 120,
  "reason": "..."}]}"""


# Return the date and time as text, for example 2026-10-13 14:05.
def now_text():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


# Return the agent mode for this campaign.
# choice is the --agent option of vtriage auto, or None. Without it,
# AGENT_MODE from local_settings.py applies to every campaign.
# An unknown value counts as off, so a typo never turns the agent on,
# and a warning is printed.
def agent_mode(choice):
    if choice is not None:
        text = str(choice)
    else:
        text = str(config.AGENT_MODE)

    mode = text.strip().lower()
    if mode not in MODES:
        print("Warning: agent mode " + text + " is not off, ask, or"
              " auto. The agent stays off.")
        return "off"
    return mode


# Return True if a path is the root folder or inside it.
# Links are followed first, so a link cannot point outside the root.
def inside_root(path, root):
    return agent.is_under(os.path.realpath(path), root)


# Return a folder path relative to the root, for summaries.
def short_path(path, root):
    relative = os.path.relpath(path, root)
    if relative == ".":
        return os.path.basename(root)
    return relative


# ---------------------------------------------------------------
# State file: what the agent decided for each folder and run
# ---------------------------------------------------------------

def state_path(root):
    return os.path.join(root, config.AGENT_STATE_NAME)


# Read a JSON file written by this agent.
# A damaged file, for example from a job killed while writing it, is
# renamed to NAME.broken_DATE and a warning is printed, so the cycle
# goes on instead of stopping with an error.
# Return the data, or None if the file is missing or damaged.
def read_json(path):
    if not os.path.isfile(path):
        return None

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except ValueError:
        data = None

    if isinstance(data, dict):
        return data

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    broken = path + ".broken_" + stamp
    try:
        os.rename(path, broken)
    except OSError:
        broken = path
    print("Warning: " + path + " was damaged. Kept as " + broken
          + ". Starting with an empty one.")
    return None


# Write a JSON file in one step: write a temporary file, then rename
# it. A job killed halfway leaves the old file, never half a file.
def write_json(path, data):
    temporary = path + ".tmp"
    with open(temporary, "w") as f:
        json.dump(data, f, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(temporary, path)


# Read agent_state.json. Return an empty state if it does not exist
# or is damaged.
def read_state(root):
    state = {"cost_total": 0.0, "llm_calls": 0, "folders": {}}
    saved = read_json(state_path(root))
    if saved is None:
        return state

    for key in state:
        if key in saved:
            state[key] = saved[key]
    if not isinstance(state["folders"], dict):
        state["folders"] = {}
    return state


def write_state(root, state):
    write_json(state_path(root), state)


# Return the saved entry for a folder if it belongs to the current
# run, or None. A new run has a new job ID, so an old entry no longer
# applies and the folder is looked at again.
def entry_for(state, record):
    entry = state["folders"].get(record["path"])
    if entry is None:
        return None
    if entry.get("job_id") != record["job_id"]:
        return None
    return entry


# Save the decision for a folder's current run.
# extra holds more values to keep, such as the new job ID.
def save_entry(state, path, job_id, decision, note, extra=None):
    entry = {"job_id": job_id,
             "decision": decision,
             "note": note,
             "date": now_text()}
    if extra is not None:
        for key in extra:
            entry[key] = extra[key]
    state["folders"][path] = entry


# Count the agent restarts and NELM reruns that led to the current run.
# The count follows the job IDs: when the agent submits a job, it keeps
# the new job ID. If the current run came from that job, the counts go
# on. If not, you submitted the folder yourself, so they start at 0.
# Return (restarts, reruns).
def chain_counts(state, record):
    entry = state["folders"].get(record["path"])
    if entry is None:
        return 0, 0
    if entry.get("decision") != "acted":
        return 0, 0
    if entry.get("new_job_id") is None:
        return 0, 0
    if entry.get("new_job_id") != record["job_id"]:
        return 0, 0
    return entry.get("restarts", 0), entry.get("reruns", 0)


# ---------------------------------------------------------------
# Plan file: actions waiting for vtriage approve (ask mode)
# ---------------------------------------------------------------

def plan_path(root):
    return os.path.join(root, config.AGENT_PLAN_NAME)


# Read agent_plan.json. Return None if there is no plan, or if it is
# damaged.
def read_plan(root):
    plan = read_json(plan_path(root))
    if plan is None:
        return None
    if not isinstance(plan.get("actions"), list):
        return None
    return plan


def write_plan(root, plan):
    write_json(plan_path(root), plan)


def remove_plan(root):
    try:
        os.remove(plan_path(root))
    except OSError:
        pass


# Return True if the plan already holds this folder and run.
def in_plan(plan, record):
    if plan is None:
        return False
    for action in plan["actions"]:
        if (action["path"] == record["path"]
                and action["job_id"] == record["job_id"]):
            return True
    return False


# ---------------------------------------------------------------
# Rules: sort each finished folder into one kind of case
# ---------------------------------------------------------------

# Make one case dictionary.
# restarts and reruns are the agent actions that led to this run.
def make_case(record, kind, note, restarts=0, reruns=0):
    return {"path": record["path"],
            "job_id": record["job_id"],
            "status": record["status"],
            "kind": kind,
            "note": note,
            "restarts": restarts,
            "reruns": reruns}


# Return None if the INCAR describes an ionic relaxation, or a note
# that says why it does not. VASP uses IBRION 0, MD, when NSW is above
# 0 and IBRION is not set.
def not_relaxation(calc_dir):
    text = parse.get_incar_value(calc_dir, "IBRION")
    ibrion = classify.to_int(text, 0)
    if ibrion in RELAX_IBRION:
        return None
    if text is None:
        return "not a relaxation (IBRION not set, so MD), not restarted"
    return ("not a relaxation (IBRION=" + str(ibrion) + "), not"
            " restarted")


# Return the energy rise allowed after a restart, in eV:
# AGENT_ENERGY_RISE_PER_ATOM times the atoms in POSCAR.
# A restarted cell relaxation can end a little higher, because the
# plane wave basis is set up again. Return 0 if POSCAR has no counts.
def energy_tolerance(calc_dir):
    atoms = evidence.atom_count(calc_dir)
    if atoms is None:
        return 0.0
    return config.AGENT_ENERGY_RISE_PER_ATOM * atoms


# Check the CONTCAR restart limits for a relaxation.
# Return None if a restart is allowed, or (kind, note) if not.
def restart_blocked(record, restarts):
    calc_dir = record["path"]

    if restarts >= config.AGENT_MAX_IONIC_RESTARTS:
        return (KIND_WAIT, "not converged after "
                + str(restarts + 1) + " runs, the most allowed")

    safe, reason = resubmit.check_contcar(calc_dir)
    if not safe:
        return (KIND_SKIP, reason)
    if not evidence.contcar_complete(calc_dir):
        return (KIND_SKIP, "CONTCAR is cut short")

    # After an agent restart, the energy must not have gone up by more
    # than the tolerance
    if restarts >= 1:
        oszicar = os.path.join(calc_dir, config.OSZICAR_NAME)
        energies = evidence.ionic_energies(oszicar)
        previous = evidence.previous_run_energy(calc_dir)
        allowed = energy_tolerance(calc_dir)
        if len(energies) > 0 and previous is not None:
            if energies[-1] > previous + allowed:
                return (KIND_WAIT, "no energy drop since the last"
                        " restart: " + "%.6f" % previous + " eV before, "
                        + "%.6f" % energies[-1] + " eV now, more than "
                        + "%.4f" % allowed + " eV higher")

    return None


# Sort one folder into a case. Return None for folders the agent
# leaves alone: running, not submitted, missing inputs, converged.
# state gives the run counts, see chain_counts.
def triage(record, root, state):
    status = record["status"]
    calc_dir = record["path"]

    if not inside_root(calc_dir, root):
        return None

    nsw = classify.to_int(parse.get_incar_value(calc_dir, "NSW"), 0)
    nelm = classify.to_int(parse.get_incar_value(calc_dir, "NELM"),
                           config.DEFAULT_NELM)
    restarts, reruns = chain_counts(state, record)

    if status == config.STATUS_RELAX_DONE_CRASHED:
        return make_case(record, KIND_DONE, "reached required accuracy"
                         " before the job died, treated as done")

    # Without a slurm file the job ID is unknown, so one run cannot be
    # told from the next
    acting = [config.STATUS_IONIC_NOT_CONVERGED,
              config.STATUS_SCF_NOT_CONVERGED]
    if status in acting and record["job_id"] is None:
        return make_case(record, KIND_WAIT, "no slurm file to read, the"
                         " agent cannot track runs here")

    if status == config.STATUS_IONIC_NOT_CONVERGED:
        note = not_relaxation(calc_dir)
        if note is not None:
            return make_case(record, KIND_WAIT, note)
        blocked = restart_blocked(record, restarts)
        if blocked is not None:
            return make_case(record, blocked[0], blocked[1])
        return make_case(record, KIND_LLM_IONIC, "", restarts, reruns)

    if (status == config.STATUS_CRASHED
            and record["message_label"] == WALLTIME_LABEL):
        if nsw <= 0:
            return make_case(record, KIND_WAIT,
                             "walltime hit on a static run")
        note = not_relaxation(calc_dir)
        if note is not None:
            return make_case(record, KIND_WAIT, "walltime hit, " + note)
        if record["scf_at_nelm"]:
            return make_case(record, KIND_WAIT, "walltime hit while the"
                             " last electronic loop was at NELM")
        blocked = restart_blocked(record, restarts)
        if blocked is not None:
            return make_case(record, blocked[0], blocked[1])
        return make_case(record, KIND_RESTART, "walltime hit, no VASP"
                         " error", restarts, reruns)

    if status == config.STATUS_SCF_NOT_CONVERGED:
        if reruns >= config.AGENT_MAX_SCF_RERUNS:
            return make_case(record, KIND_WAIT, "SCF not converged after "
                             + str(reruns + 1) + " runs, the most"
                             " allowed")
        if nelm >= config.AGENT_MAX_NELM:
            return make_case(record, KIND_WAIT, "NELM is already "
                             + str(nelm) + ", the largest allowed")
        if nsw > 0:
            note = not_relaxation(calc_dir)
            if note is not None:
                return make_case(record, KIND_WAIT, note)
            safe, reason = resubmit.check_contcar(calc_dir)
            if not safe:
                return make_case(record, KIND_SKIP, reason)
            if not evidence.contcar_complete(calc_dir):
                return make_case(record, KIND_SKIP, "CONTCAR is cut"
                                 " short")
        return make_case(record, KIND_LLM_SCF, "", restarts, reruns)

    if status == config.STATUS_CRASHED:
        return make_case(record, KIND_WAIT, "crashed: "
                         + str(record["message_label"]))

    if status == config.STATUS_INCOMPLETE:
        return make_case(record, KIND_WAIT, "stopped without a known"
                         " error, possibly a node failure")

    return None


# ---------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------

# Build the message with the evidence for each case.
# Each case gets an id such as F1, stored in case["id"].
def build_message(cases, root):
    lines = []
    lines.append("Decide for each folder below. Reply with JSON only.")

    number = 0
    for case in cases:
        number = number + 1
        case["id"] = "F" + str(number)
        calc_dir = case["path"]

        lines.append("")
        lines.append("Folder " + case["id"] + ": "
                     + short_path(calc_dir, root))

        if case["kind"] == KIND_LLM_IONIC:
            restarts = case["restarts"]
            lines.append("Kind: ionic")
            lines.append("Allowed decisions: restart, wait")
            lines.append("This was run " + str(restarts + 1)
                         + " of at most "
                         + str(config.AGENT_MAX_IONIC_RESTARTS + 1)
                         + " in this folder.")
            lines.append(evidence.ionic_evidence(calc_dir))
        else:
            nelm = classify.to_int(
                parse.get_incar_value(calc_dir, "NELM"),
                config.DEFAULT_NELM)
            lines.append("Kind: scf")
            lines.append("Allowed decisions: rerun, wait")
            lines.append("Current NELM: " + str(nelm)
                         + ". Largest NELM allowed: "
                         + str(config.AGENT_MAX_NELM) + ".")
            lines.append(evidence.scf_evidence(calc_dir))

    return "\n".join(lines) + "\n"


# Find the claude program. scrontab jobs do not read ~/.bashrc, so
# PATH may not include it. Return the full path, or None.
def find_claude():
    command = config.AGENT_CLAUDE_COMMAND
    if os.sep in command:
        path = os.path.expanduser(command)
        if os.path.isfile(path):
            return path
        return None

    found = shutil.which(command)
    if found is not None:
        return found

    # The usual place after the Claude Code installer
    fallback = os.path.expanduser("~/.local/bin/claude")
    if os.path.isfile(fallback):
        return fallback
    return None


# Take the JSON object out of the LLM answer.
# Return the list of decisions, or None if the answer is not valid.
def read_answer(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None

    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return None

    if not isinstance(data, dict):
        return None
    decisions = data.get("decisions")
    if not isinstance(decisions, list):
        return None
    return decisions


# Ask the LLM once about all cases.
# Return (decisions or None, cost in USD, error text or "").
def call_llm(root, message):
    claude = find_claude()
    if claude is None:
        return None, 0.0, "claude not found, set AGENT_CLAUDE_COMMAND"

    # The prompt comes right after -p, because some options take
    # several values and would swallow a prompt placed after them.
    # --tools "" removes every built in tool, and --disallowedTools
    # removes every MCP tool, so the LLM can only answer in text.
    command = [claude, "-p", message,
               "--model", config.AGENT_MODEL,
               "--output-format", "json",
               "--system-prompt", SYSTEM_PROMPT,
               "--max-turns", "1",
               "--max-budget-usd", str(config.AGENT_COST_PER_PASS),
               "--no-session-persistence",
               "--strict-mcp-config",
               "--tools", "",
               "--disallowedTools", "mcp__*"]

    try:
        result = subprocess.run(command,
                                cwd=root,
                                stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True,
                                timeout=config.AGENT_CALL_SECONDS)
    except subprocess.TimeoutExpired:
        return None, 0.0, ("no answer within "
                           + str(config.AGENT_CALL_SECONDS) + " s")
    except OSError as error:
        return None, 0.0, "claude could not start: " + str(error)

    try:
        data = json.loads(result.stdout)
    except ValueError:
        text = (result.stderr.strip() + " " + result.stdout.strip())
        return None, 0.0, "unreadable output: " + text[:300]

    cost = data.get("total_cost_usd", 0.0)
    if cost is None:
        cost = 0.0

    if data.get("is_error") or result.returncode != 0:
        detail = str(data.get("subtype", "")) + " " + \
            str(data.get("result", ""))
        return None, cost, "claude error: " + detail.strip()[:300]

    decisions = read_answer(str(data.get("result", "")))
    if decisions is None:
        return None, cost, "answer was not the expected JSON"

    return decisions, cost, ""


# Clean the reason text from the LLM: one line, at most 300 letters.
def clean_reason(value):
    text = " ".join(str(value).split())
    if len(text) > 300:
        text = text[:297] + "..."
    return text


# Check one LLM decision against the rules.
# Return (action, nelm, reason). action is restart, rerun, or wait.
# Anything outside the rules becomes wait.
def check_decision(case, item):
    if item is None:
        return "wait", None, "the LLM gave no decision for this folder"

    reason = clean_reason(item.get("reason", ""))
    decision = str(item.get("decision", "")).strip().lower()

    if decision == "wait":
        return "wait", None, reason

    if case["kind"] == KIND_LLM_IONIC:
        if decision == "restart":
            return "restart", None, reason
        return "wait", None, "the LLM answered " + decision \
            + ", which is not allowed here"

    # scf case
    if decision != "rerun":
        return "wait", None, "the LLM answered " + decision \
            + ", which is not allowed here"

    current = classify.to_int(
        parse.get_incar_value(case["path"], "NELM"),
        config.DEFAULT_NELM)
    new_nelm = classify.to_int(str(item.get("nelm", "")), None)

    if new_nelm is None or new_nelm <= current:
        return "wait", None, "the LLM asked for a rerun without a" \
            " larger NELM"
    if new_nelm > config.AGENT_MAX_NELM:
        new_nelm = config.AGENT_MAX_NELM
    return "rerun", new_nelm, reason


# ---------------------------------------------------------------
# Actions. Only these change files or submit jobs.
# ---------------------------------------------------------------

# Run sbatch in one folder.
# Return (job ID, "") on success, or (None, error text) if sbatch
# refused the job.
def submit_job(calc_dir):
    command = ["sbatch", config.JOB_SCRIPT_NAME]

    try:
        result = subprocess.run(command,
                                cwd=calc_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
    except FileNotFoundError:
        return None, "sbatch not found"

    if result.returncode != 0:
        text = " ".join(result.stderr.split())
        if text == "":
            text = "sbatch exit code " + str(result.returncode)
        return None, text[:200]

    # sbatch prints: Submitted batch job 300200
    words = result.stdout.split()
    if len(words) == 0 or not words[-1].isdigit():
        return None, "could not read the job ID: " + result.stdout.strip()

    return words[-1], ""


# Restart a relaxation from CONTCAR, or raise NELM and rerun.
# action is restart or rerun. restarts is the run count before it.
# If sbatch refuses the job, INCAR and POSCAR are put back as they
# were, so a later try starts from the same files.
# Return (new job ID or None, note, error text).
def apply_action(case, action, nelm, reason, root, queued_dirs):
    calc_dir = case["path"]

    # Safety checks again, right before anything is written
    if not inside_root(calc_dir, root):
        return None, "outside the root folder, nothing done", ""
    if os.path.realpath(calc_dir) in queued_dirs:
        return None, "job is in the queue, nothing done", ""

    # Save the finished run first, as NAME-N and in progress.txt.
    # On a later try it is already saved and is skipped.
    history.archive_one(calc_dir, queued_dirs)

    nsw = classify.to_int(parse.get_incar_value(calc_dir, "NSW"), 0)
    incar_path = os.path.join(calc_dir, config.INCAR_NAME)
    poscar_path = os.path.join(calc_dir, config.POSCAR_NAME)
    contcar_path = os.path.join(calc_dir, config.CONTCAR_NAME)

    # Keep the old files, to put them back if sbatch refuses the job
    old_incar = parse.read_lines(incar_path)
    old_poscar = parse.read_lines(poscar_path)

    if action == "restart":
        shutil.copy2(contcar_path, poscar_path)
        run_text = ("run " + str(case["restarts"] + 2) + " of "
                    + str(config.AGENT_MAX_IONIC_RESTARTS + 1))
        line = PROGRESS_RESTART + ", " + run_text + ". " + reason
        note = "restarted from CONTCAR, " + run_text
    else:
        old_nelm = classify.to_int(
            parse.get_incar_value(calc_dir, "NELM"),
            config.DEFAULT_NELM)
        new_lines, changes = edit.plan_incar(old_incar,
                                             [("NELM", str(nelm))], [])
        edit.write_lines(incar_path, new_lines)

        # A relaxation continues from where it stopped
        if nsw > 0:
            shutil.copy2(contcar_path, poscar_path)

        line = (PROGRESS_NELM + " " + str(old_nelm) + " -> " + str(nelm)
                + ", SCF rerun. " + reason)
        note = "NELM " + str(old_nelm) + " -> " + str(nelm) + ", rerun"

    job_id, error = submit_job(calc_dir)
    if job_id is None:
        edit.write_lines(incar_path, old_incar)
        edit.write_lines(poscar_path, old_poscar)
        return None, note, error

    history.append_progress(calc_dir, "  " + line + "\n\n")
    return job_id, note + ", job " + job_id, ""


# Save the result of one action in the state, and return
# (group title, text, submitted) for the summary.
# tries is how often sbatch refused this action before.
def record_action(state, case, action, nelm, reason, source, result,
                  tries, first_error, approved):
    job_id, note, error = result
    calc_dir = case["path"]

    label = source + ": " + reason
    if approved:
        label = "Approved by you. " + label

    # Not submitted for a reason that is not sbatch, such as a job
    # already in the queue: nothing was changed
    if job_id is None and error == "":
        text = note + ". " + label
        save_entry(state, calc_dir, case["job_id"], "wait", text)
        return GROUP_FAILED, text, False

    if job_id is not None:
        text = note + ". " + label
        if tries > 0:
            text = (text + " Submitted on try " + str(tries + 1)
                    + ", the first submit failed: " + first_error)
        restarts = case["restarts"]
        reruns = case["reruns"]
        if action == "restart":
            restarts = restarts + 1
            group = GROUP_RESTARTED
        else:
            reruns = reruns + 1
            group = GROUP_RERUN
        save_entry(state, calc_dir, case["job_id"], "acted", text,
                   {"new_job_id": job_id, "restarts": restarts,
                    "reruns": reruns})
        return group, text, True

    # sbatch refused the job. The files were put back.
    if action == "restart":
        planned = "restart from CONTCAR"
    else:
        planned = "NELM rerun with NELM " + str(nelm)
    tries = tries + 1
    if first_error == "":
        first_error = error

    if tries >= config.AGENT_SUBMIT_TRIES:
        text = (planned + " was planned, but sbatch refused it "
                + str(tries) + " times. Last error: " + error
                + ". Files unchanged. " + label)
        save_entry(state, calc_dir, case["job_id"], "wait", text)
        return GROUP_FAILED, text, False

    text = (planned + " refused by sbatch: " + error + ". Try "
            + str(tries) + " of " + str(config.AGENT_SUBMIT_TRIES)
            + ". " + label)
    save_entry(state, calc_dir, case["job_id"], "retry", text,
               {"action": action, "nelm": nelm, "reason": reason,
                "source": source, "tries": tries,
                "first_error": first_error, "approved": approved,
                "restarts": case["restarts"],
                "reruns": case["reruns"]})
    return GROUP_RETRY, text, False


# ---------------------------------------------------------------
# Summary and email
# ---------------------------------------------------------------

# Build the plain English summary of one cycle.
# events: list of (group title, short path, text)
def make_summary(root, mode, events, cost_now, state, extra_lines):
    lines = []
    lines.append("vtriage agent, " + now_text())
    lines.append("Root: " + root)
    lines.append("Mode: " + mode + ". LLM cost this cycle: "
                 + "%.4f" % cost_now + " USD. Campaign total: "
                 + "%.4f" % state["cost_total"] + " of "
                 + "%.2f" % config.AGENT_COST_CAMPAIGN + " USD.")

    for title in GROUP_TITLES:
        items = []
        for group, path_text, text in events:
            if group == title:
                items.append("  " + path_text + ": " + text)
        if len(items) == 0:
            continue
        lines.append("")
        lines.append(title + " (" + str(len(items)) + "):")
        lines.extend(items)

    if len(extra_lines) > 0:
        lines.append("")
        lines.extend(extra_lines)

    return "\n".join(lines) + "\n"


# Count the events in one group.
def count_group(events, title):
    count = 0
    for group, path_text, text in events:
        if group == title:
            count = count + 1
    return count


# Submit a one minute job that prints the summary. Slurm sends the
# email when it ends, and the job name shows the counts in the
# subject. Return a line that says what happened.
def send_email(root, subject_name):
    if config.AUTO_EMAIL == "":
        return "Email: not sent, AUTO_EMAIL is empty."

    command = (["sbatch"] + config.AUTO_EMAIL_SBATCH_OPTIONS
               + ["-J", subject_name,
                  "-o", "vtriage_agent.out",
                  "--mail-type=END",
                  "--mail-user=" + config.AUTO_EMAIL,
                  "--wrap=cat " + config.AGENT_SUMMARY_NAME])

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

    return "Email: " + result.stdout.strip() + ", to " + config.AUTO_EMAIL


# Keep letters, digits, _ and - so the text is safe in a job name.
def safe_name(text):
    kept = ""
    for letter in text:
        if letter.isalnum() or letter in "_-":
            kept = kept + letter
        else:
            kept = kept + "_"
    return kept


# Write the summary file, log it, and send the email.
def report_cycle(root, summary, subject_name):
    summary_path = os.path.join(root, config.AGENT_SUMMARY_NAME)
    with open(summary_path, "w") as f:
        f.write(summary)

    email_line = send_email(root, subject_name)
    print(summary)
    print(email_line)

    # agent_log.txt in the root, and the activity log on GitHub
    agent.write_log(root, "agent cycle", "decisions made",
                    summary + "\n" + email_line)


# ---------------------------------------------------------------
# One cycle, called by auto.py
# ---------------------------------------------------------------
# A cycle keeps its working values in one dictionary:
#   state     agent_state.json, saved at the end
#   events    what happened, as (group title, short path, text)
#   extra     extra lines for the summary
#   deferred  folders put off to the next cycle
#   cost      money spent on the LLM in this cycle

# Record a decision that needs no job: done, wait, or skip.
def record_decision(cycle, case, group, decision, note, root):
    cycle["events"].append((group, short_path(case["path"], root), note))
    save_entry(cycle["state"], case["path"], case["job_id"], decision,
               note)


# Sort the folders that are new to the agent.
# Done, wait, and skip cases are recorded at once.
# Return (rule actions, cases for the LLM).
def sort_cases(cycle, records, plan, root):
    rule_actions = []
    llm_cases = []

    for record in records:
        if entry_for(cycle["state"], record) is not None:
            continue
        if in_plan(plan, record):
            continue

        case = triage(record, root, cycle["state"])
        if case is None:
            continue

        if case["kind"] == KIND_DONE:
            record_decision(cycle, case, GROUP_DONE, "done",
                            case["note"], root)
        elif case["kind"] == KIND_WAIT:
            record_decision(cycle, case, GROUP_WAIT, "wait",
                            case["note"], root)
        elif case["kind"] == KIND_SKIP:
            record_decision(cycle, case, GROUP_SKIP, "skip",
                            case["note"], root)
        elif case["kind"] == KIND_RESTART:
            rule_actions.append(case)
        else:
            llm_cases.append(case)

    return rule_actions, llm_cases


# Ask the LLM about the cases that need judgment, at most limit of
# them. Return a list of (case, action, nelm, reason, source) for the
# cases it allows. Cases it does not allow are recorded as waiting.
def judge_cases(cycle, llm_cases, limit, root):
    chosen = []
    if len(llm_cases) == 0:
        return chosen

    # Campaign limit reached: no more calls, a person decides
    if cycle["state"]["cost_total"] >= config.AGENT_COST_CAMPAIGN:
        note = ("campaign LLM cost limit of "
                + "%.2f" % config.AGENT_COST_CAMPAIGN
                + " USD reached, not judged")
        for case in llm_cases:
            record_decision(cycle, case, GROUP_WAIT, "wait", note, root)
        return chosen

    if limit < 0:
        limit = 0
    asked = llm_cases[:limit]
    cycle["deferred"] = cycle["deferred"] + len(llm_cases) - len(asked)
    if len(asked) == 0:
        return chosen

    message = build_message(asked, root)
    decisions, cost, error = call_llm(root, message)
    cycle["cost"] = cycle["cost"] + cost
    cycle["state"]["cost_total"] = cycle["state"]["cost_total"] + cost
    cycle["state"]["llm_calls"] = cycle["state"]["llm_calls"] + 1

    if decisions is None:
        # Nothing is saved, so these folders are tried again next
        # cycle. The campaign cost limit stops endless repeats.
        cycle["deferred"] = cycle["deferred"] + len(asked)
        cycle["extra"].append("LLM call failed: " + error
                              + ". Tried again next cycle.")
        return chosen

    by_id = {}
    for item in decisions:
        if isinstance(item, dict) and "id" in item:
            by_id[str(item["id"])] = item

    for case in asked:
        action, nelm, reason = check_decision(case,
                                              by_id.get(case["id"]))
        if action == "wait":
            record_decision(cycle, case, GROUP_WAIT, "wait",
                            "LLM: " + reason, root)
        else:
            chosen.append((case, action, nelm, reason, "LLM"))

    return chosen


# Auto mode: apply each chosen action and submit.
# Return the number of jobs submitted.
def act_now(cycle, chosen, root):
    submitted = 0
    queued_dirs = classify.get_queued_dirs()

    for case, action, nelm, reason, source in chosen:
        result = apply_action(case, action, nelm, reason, root,
                              queued_dirs)
        group, text, done = record_action(cycle["state"], case, action,
                                          nelm, reason, source, result,
                                          0, "", False)
        cycle["events"].append((group, short_path(case["path"], root),
                                text))
        if done:
            submitted = submitted + 1

    return submitted


# Try again the submits that sbatch refused in an earlier cycle, at
# most slots of them. No new LLM call is made: the saved action is
# applied again. Return (jobs submitted, folders still to try).
def retry_submits(cycle, records, slots, root):
    submitted = 0
    waiting = 0
    queued_dirs = None

    for record in records:
        entry = entry_for(cycle["state"], record)
        if entry is None or entry.get("decision") != "retry":
            continue

        # Submitted by hand in the meantime: the new run decides
        if record["status"] == config.STATUS_RUNNING:
            continue

        if slots is not None and submitted >= slots:
            waiting = waiting + 1
            continue

        if queued_dirs is None:
            queued_dirs = classify.get_queued_dirs()

        case = make_case(record, "retry", "", entry.get("restarts", 0),
                         entry.get("reruns", 0))
        result = apply_action(case, entry["action"], entry.get("nelm"),
                              entry["reason"], root, queued_dirs)
        group, text, done = record_action(cycle["state"], case,
                                          entry["action"],
                                          entry.get("nelm"),
                                          entry["reason"],
                                          entry["source"], result,
                                          entry.get("tries", 0),
                                          entry.get("first_error", ""),
                                          entry.get("approved", False))
        cycle["events"].append((group, short_path(case["path"], root),
                                text))
        if done:
            submitted = submitted + 1
        elif group == GROUP_RETRY:
            waiting = waiting + 1

    return submitted, waiting


# Ask mode: add each chosen action to agent_plan.json.
def add_to_plan(cycle, chosen, plan, root):
    if plan is None:
        plan = {"root": root, "created": now_text(), "actions": []}

    for case, action, nelm, reason, source in chosen:
        plan["actions"].append({"path": case["path"],
                                "job_id": case["job_id"],
                                "status": case["status"],
                                "action": action,
                                "nelm": nelm,
                                "reason": reason,
                                "source": source,
                                "date": now_text()})
        if action == "restart":
            text = "restart from CONTCAR"
        else:
            text = "raise NELM to " + str(nelm) + " and rerun"
        cycle["events"].append((GROUP_PLANNED,
                                short_path(case["path"], root),
                                text + ". " + source + ": " + reason))

    write_plan(root, plan)
    cycle["extra"].append("Run vtriage approve --root " + root
                          + " to see and apply the plan.")


# Write the summary and send the email, if anything new happened.
def tell_user(cycle, mode, submitted, root):
    if cycle["deferred"] > 0:
        cycle["extra"].append(str(cycle["deferred"])
                              + " folder(s) put off to the next"
                              " cycle.")

    if len(cycle["events"]) == 0:
        for line in cycle["extra"]:
            print("Agent: " + line)
        return

    summary = make_summary(root, mode, cycle["events"], cycle["cost"],
                           cycle["state"], cycle["extra"])

    waiting = (count_group(cycle["events"], GROUP_WAIT)
               + count_group(cycle["events"], GROUP_FAILED)
               + count_group(cycle["events"], GROUP_SKIP))
    base = safe_name(os.path.basename(root))
    if mode == "ask":
        planned = count_group(cycle["events"], GROUP_PLANNED)
        name = (config.AUTO_HELPER_PREFIX + "plan_" + base + "_"
                + str(planned) + "toapprove_" + str(waiting) + "you")
    else:
        name = (config.AUTO_HELPER_PREFIX + "agent_" + base + "_"
                + str(submitted) + "acted_" + str(waiting) + "you")

    report_cycle(root, summary, name)


# Handle the finished folders of one cycle.
# records: classified folders of this cycle, already path filtered
# free_slots: jobs that may still be submitted, or None for no limit
# mode: ask or auto, from agent_mode
# Return (jobs submitted, busy). busy is True while the agent still
# has work: a plan waits for approval, or folders were put off.
def agent_step(root, records, free_slots, mode):
    if mode == "off":
        return 0, False

    cycle = {"state": read_state(root), "events": [], "extra": [],
             "deferred": 0, "cost": 0.0}

    plan = None
    if mode == "ask":
        plan = read_plan(root)

    # Step 0: submits that sbatch refused before. They were decided
    # already, by the agent or by you, so they go in both modes.
    retried, retry_waiting = retry_submits(cycle, records, free_slots,
                                           root)
    if free_slots is not None:
        free_slots = free_slots - retried

    # Step 1: sort the folders that are new to the agent
    rule_actions, llm_cases = sort_cases(cycle, records, plan, root)

    # Step 2: in auto mode, only as many jobs as the queue allows.
    # In ask mode nothing is submitted, so there is no slot limit.
    slots = None
    if mode == "auto":
        slots = free_slots
    if slots is not None:
        if len(rule_actions) > slots:
            cycle["deferred"] = len(rule_actions) - slots
            rule_actions = rule_actions[:slots]
        slots = slots - len(rule_actions)

    chosen = []
    for case in rule_actions:
        chosen.append((case, "restart", None, case["note"], "rule"))

    # Step 3: the LLM judges the rest
    limit = config.AGENT_MAX_FOLDERS_PER_CALL
    if slots is not None and slots < limit:
        limit = slots
    chosen = chosen + judge_cases(cycle, llm_cases, limit, root)

    # Step 4: act now, or plan and wait for vtriage approve
    submitted = retried
    if len(chosen) > 0:
        if mode == "auto":
            submitted = submitted + act_now(cycle, chosen, root)
        else:
            add_to_plan(cycle, chosen, plan, root)

    write_state(root, cycle["state"])

    # Step 5: summary and email
    tell_user(cycle, mode, submitted, root)

    busy = cycle["deferred"] > 0
    if retry_waiting > 0 or count_group(cycle["events"], GROUP_RETRY) > 0:
        busy = True
    if mode == "ask" and read_plan(root) is not None:
        busy = True
    return submitted, busy


# ---------------------------------------------------------------
# Notes for AUTO_DONE
# ---------------------------------------------------------------

# Return the agent note for a folder's current run, or None.
def note_for(root, record):
    if not os.path.isfile(state_path(root)):
        return None
    state = read_state(root)
    entry = entry_for(state, record)
    if entry is None:
        return None
    return entry["decision"] + ", " + entry["note"]


# Return one line with the money the LLM cost in this campaign.
def cost_line(root):
    if not os.path.isfile(state_path(root)):
        return None
    state = read_state(root)
    return ("Agent LLM cost: " + "%.4f" % state["cost_total"]
            + " USD in " + str(state["llm_calls"]) + " calls")


# ---------------------------------------------------------------
# vtriage approve
# ---------------------------------------------------------------

# Turn the answer into a list of plan positions, starting at 0.
# yes gives all, no gives none, 1 3 gives the first and the third.
# Return None if the answer cannot be read.
def read_choice(answer, count):
    text = answer.strip().lower()
    if text == "yes":
        return list(range(count))
    if text == "no" or text == "":
        return []

    chosen = []
    for word in text.replace(",", " ").split():
        if not word.isdigit():
            return None
        number = int(word)
        if number < 1 or number > count:
            return None
        if number - 1 not in chosen:
            chosen.append(number - 1)
    return chosen


# Show the plan, ask once, and apply the approved actions.
# Folders whose status or job changed since the plan are skipped.
# Folders not approved are marked as waiting for you.
def do_approve(root):
    # Hold the auto lock, so a scheduled cycle cannot act on the same
    # folders at the same time. auto.py imports this file, so it is
    # imported here.
    import auto
    if not auto.take_lock(root):
        print("An auto cycle is running now. Try again in a minute.")
        return 1

    try:
        return approve_with_lock(root)
    finally:
        auto.release_lock(root)


# The part of do_approve that runs while the lock is held.
def approve_with_lock(root):
    plan = read_plan(root)
    if plan is None:
        print("No plan waiting in " + root)
        return 0

    actions = plan["actions"]
    print("Plan made " + plan.get("created", "") + " for " + root)
    print("")
    number = 0
    for item in actions:
        number = number + 1
        if item["action"] == "restart":
            what = "restart from CONTCAR"
        else:
            what = "raise NELM to " + str(item["nelm"]) + " and rerun"
        print(str(number) + ". " + short_path(item["path"], root) + ": "
              + what)
        print("   " + item["source"] + ": " + item["reason"])

    print("")
    answer = input("Type yes to apply all, no to reject all, or the"
                   " numbers to apply, such as 1 3: ")
    chosen = read_choice(answer, len(actions))
    if chosen is None:
        print("Answer not understood. Nothing changed. The plan is"
              " kept.")
        return 1

    state = read_state(root)
    queued_dirs = classify.get_queued_dirs()
    lines = []

    for index in range(len(actions)):
        item = actions[index]
        calc_dir = item["path"]
        path_text = short_path(calc_dir, root)

        if index not in chosen:
            save_entry(state, calc_dir, item["job_id"], "wait",
                       "rejected by you")
            lines.append("Rejected: " + path_text)
            continue

        # Check that nothing changed since the plan was made
        record = classify.classify(calc_dir, queued_dirs)
        if (record["status"] != item["status"]
                or record["job_id"] != item["job_id"]):
            lines.append("Changed since the plan, skipped: " + path_text)
            continue

        case = triage(record, root, state)
        allowed = [KIND_RESTART, KIND_LLM_IONIC, KIND_LLM_SCF]
        if case is None or case["kind"] not in allowed:
            note = "no longer allowed"
            if case is not None:
                note = case["note"]
            save_entry(state, calc_dir, item["job_id"], "wait", note)
            lines.append("Not allowed now (" + note + "): " + path_text)
            continue

        result = apply_action(case, item["action"], item["nelm"],
                              item["reason"], root, queued_dirs)
        group, text, done = record_action(state, case, item["action"],
                                          item["nelm"], item["reason"],
                                          item["source"], result, 0, "",
                                          True)
        lines.append(path_text + ": " + text)

    write_state(root, state)
    remove_plan(root)

    print("")
    for line in lines:
        print(line)
    return 0


def read_arguments():
    parser = argparse.ArgumentParser(
        description="Decision agent: show and apply the waiting plan.")
    parser.add_argument("action", choices=["approve"],
                        help="approve shows the plan and asks once")
    parser.add_argument("--root", default=".",
                        help="campaign root, default is this folder")
    return parser.parse_args()


if __name__ == "__main__":
    args = read_arguments()

    root = os.path.abspath(scan.resolve_path(args.root))
    if not os.path.isdir(root):
        print("Error: not a directory: " + root)
        sys.exit(1)

    if args.action == "approve":
        sys.exit(do_approve(root))
