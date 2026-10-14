# local_settings.py
# Per machine settings for vasp_triage.
# Copy this file to the vasp_triage folder as local_settings.py and
# edit the values. git ignores local_settings.py, so a git pull never
# overwrites it. Anything set here overrides config.py.

# ---------------------------------------------------------------
# Submit limits (vtriage submit)
# ---------------------------------------------------------------
# Largest number of jobs submitted by one submit command
MAX_SUBMIT = 20

# Largest number of my jobs in the queue at once, all projects.
# 0 turns the limit off.
QUEUE_LIMIT = 15

# ---------------------------------------------------------------
# Auto agent (vtriage auto)
# ---------------------------------------------------------------
# New jobs submitted per cycle
AUTO_BATCH = 20

# Largest number of my jobs in the queue at once. Jobs whose name
# starts with vtriage_ are helpers and are not counted.
AUTO_QUEUE_LIMIT = 30

# Address for the completion email. Empty means no email.
AUTO_EMAIL = "you@example.com"

# sbatch options for the one minute email job. Use a queue that
# charges only the cores used, such as shared on NERSC Perlmutter.
AUTO_EMAIL_SBATCH_OPTIONS = ["-A", "YOUR_ACCOUNT", "-q", "shared",
                             "-C", "cpu", "-n", "1", "-c", "2",
                             "-t", "1"]

# ---------------------------------------------------------------
# Schedule (vtriage schedule), NERSC Perlmutter only
# ---------------------------------------------------------------
# NERSC account for the scrontab job. Empty means use the -A value
# in AUTO_EMAIL_SBATCH_OPTIONS.
SCHEDULE_ACCOUNT = ""

# Time between cycles when --every is not given, such as 20m or 5h
SCHEDULE_EVERY = "5h"

# ---------------------------------------------------------------
# Shared activity log across machines (optional)
# ---------------------------------------------------------------
# Folder of a private git repository that collects every command
# from every machine. Empty means off.
ACTIVITY_LOG_DIR = ""

# Name of this machine in the log. Set it by hand.
MACHINE_NAME = ""

# Push the log folder to its remote after each command.
ACTIVITY_LOG_PUSH = False

# ---------------------------------------------------------------
# Decision agent (decide.py), optional, NERSC Perlmutter
# ---------------------------------------------------------------
# off: nothing. ask: plan only, apply with vtriage approve.
# auto: allowed actions are applied and submitted at once.
# This applies to every campaign started without --agent. Keep it
# off and use vtriage schedule --agent ask for one campaign.
AGENT_MODE = "off"

# CONTCAR restarts per folder (2 means 3 runs in all), NELM reruns
# per folder (1 means 2 runs in all), largest NELM
AGENT_MAX_IONIC_RESTARTS = 2
AGENT_MAX_SCF_RERUNS = 1
AGENT_MAX_NELM = 150

# Most money per LLM call and per campaign, in USD. A call for 10
# folders costs about 0.07 USD.
AGENT_COST_PER_PASS = 0.50
AGENT_COST_CAMPAIGN = 1.50

# Energy rise allowed after a restart, in eV per atom, and sbatch
# refusals allowed before a folder waits for you
AGENT_ENERGY_RISE_PER_ATOM = 0.001
AGENT_SUBMIT_TRIES = 3

# Full path to claude, since scrontab jobs do not read ~/.bashrc.
# Find it with: which claude
AGENT_CLAUDE_COMMAND = "/global/homes/u/user/.local/bin/claude"
