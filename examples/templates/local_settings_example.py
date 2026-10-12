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
