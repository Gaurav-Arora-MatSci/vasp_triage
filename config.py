# config.py
# Settings shared by all modules.
# Change values here, not inside the other files.

# ---------------------------------------------------------------
# File names inside each calculation directory
# ---------------------------------------------------------------
INCAR_NAME = "INCAR"
KPOINTS_NAME = "KPOINTS"
OUTCAR_NAME = "OUTCAR"
OSZICAR_NAME = "OSZICAR"
JOB_SCRIPT_NAME = "submit_vasp.sh"
PROGRESS_NAME = "progress.txt"

# Files a directory needs before it can be submitted
POSCAR_NAME = "POSCAR"
POTCAR_NAME = "POTCAR"
REQUIRED_INPUT_FILES = [INCAR_NAME, KPOINTS_NAME, POSCAR_NAME,
                        POTCAR_NAME, JOB_SCRIPT_NAME]

# Status for directories that lack one or more required files
STATUS_MISSING_INPUTS = "missing inputs"

# Scheduler output files look like slurm-4812345.out
SLURM_PREFIX = "slurm-"
SLURM_SUFFIX = ".out"

# Files copied to name-N before a new run is submitted
ARCHIVE_FILES = [INCAR_NAME, KPOINTS_NAME, OUTCAR_NAME, OSZICAR_NAME]
# The latest slurm file is archived too. history.py finds it by name.

# ---------------------------------------------------------------
# Reading files
# ---------------------------------------------------------------
# Number of bytes read from the end of a large file.
# 200000 bytes is about 200 KB.
TAIL_BYTES = 200000

# ---------------------------------------------------------------
# VASP defaults and markers
# ---------------------------------------------------------------
# NELM used when the INCAR does not set it
DEFAULT_NELM = 60

# Text written near the end of OUTCAR after a clean finish
NORMAL_END_TEXT = "General timing and accounting informations"

# Text on the OUTCAR line that holds the final energy
ENERGY_TEXT = "energy(sigma->0)"

# Line starts for electronic steps in OSZICAR
SCF_LINE_STARTS = ["DAV:", "RMM:", "CG :"]

# INCAR tags written to progress.txt and report.csv
KEY_INCAR_TAGS = ["ENCUT", "EDIFF", "EDIFFG", "NELM"]

# Text printed when an ionic relaxation meets EDIFFG
# Not printed for static runs (NSW = 0)
RELAX_DONE_TEXT = "reached required accuracy"

STATUS_IONIC_NOT_CONVERGED = "ionic not converged"
# ---------------------------------------------------------------
# Error patterns searched in the latest slurm file
# Each entry: (text to search for, short label for the report)
# Order matters: the first match wins.
# ---------------------------------------------------------------
ERROR_PATTERNS = [
    ("DUE TO TIME LIMIT", "walltime"),
    ("oom-kill", "out of memory"),
    ("Out Of Memory", "out of memory"),
    ("CANCELLED", "cancelled"),
    ("ZBRENT", "zbrent"),
    ("ZHEGV", "zhegv"),
    ("ZPOTRF", "zpotrf"),
    ("Sub-Space-Matrix is not hermitian", "subspace hermitian"),
    ("VERY BAD NEWS", "very bad news"),
    ("internal error in subroutine", "internal error"),
    ("Inconsistent Bravais lattice", "bravais lattice"),
    ("PRICEL", "pricel"),
    ("RSPHER", "rspher"),
    ("BRIONS problems", "brions"),
]

# ---------------------------------------------------------------
# Report groups. Each entry: (group name, list of statuses)
# The order here is the order in the report.
# ---------------------------------------------------------------
REPORT_GROUPS = [
    ("converged", [STATUS_CONVERGED]),
    ("not_converged", [STATUS_SCF_NOT_CONVERGED,
                       STATUS_IONIC_NOT_CONVERGED]),
    ("failed", [STATUS_CRASHED, STATUS_INCOMPLETE]),
    ("other", [STATUS_RUNNING, STATUS_NOT_SUBMITTED,
               STATUS_MISSING_INPUTS]),
]


# ---------------------------------------------------------------
# Status labels used in reports and progress.txt
# ---------------------------------------------------------------
STATUS_RUNNING = "running or pending"
STATUS_NOT_SUBMITTED = "not submitted"
STATUS_CRASHED = "crashed"
STATUS_INCOMPLETE = "incomplete"
STATUS_SCF_NOT_CONVERGED = "SCF not converged"
STATUS_CONVERGED = "converged"


# ---------------------------------------------------------------
# Report folder naming
# ---------------------------------------------------------------
# Month names used in report folder names
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "June",
               "July", "Aug", "Sept", "Oct", "Nov", "Dec"]
