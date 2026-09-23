
# config.py
# Settings shared by all modules.
# Change values here, not inside the other files.
# Python reads this file from top to bottom, so every name must be
# defined above the line that uses it.

# ---------------------------------------------------------------
# Package information
# ---------------------------------------------------------------
VERSION = "0.3.0"
AUTHOR = "Gaurav Arora, Villanova University"

# ---------------------------------------------------------------
# File names inside each calculation directory
# ---------------------------------------------------------------
INCAR_NAME = "INCAR"
WAVECAR_NAME = "WAVECAR"
KPOINTS_NAME = "KPOINTS"
POSCAR_NAME = "POSCAR"
POTCAR_NAME = "POTCAR"
OUTCAR_NAME = "OUTCAR"
OSZICAR_NAME = "OSZICAR"
CONTCAR_NAME = "CONTCAR"
JOB_SCRIPT_NAME = "submit_vasp.sh"
PROGRESS_NAME = "progress.txt"

# Scheduler output files look like slurm-4812345.out
SLURM_PREFIX = "slurm-"
SLURM_SUFFIX = ".out"

# Files a directory needs before it can be submitted
REQUIRED_INPUT_FILES = [INCAR_NAME, KPOINTS_NAME, POSCAR_NAME,
                        POTCAR_NAME, JOB_SCRIPT_NAME]

# Files copied to name-N before a new run is submitted
ARCHIVE_FILES = [INCAR_NAME, KPOINTS_NAME, POSCAR_NAME, CONTCAR_NAME, OUTCAR_NAME, OSZICAR_NAME]
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

# Text printed when an ionic relaxation meets EDIFFG
# Not printed for static runs (NSW = 0)
RELAX_DONE_TEXT = "reached required accuracy"

# Text on the OUTCAR line that holds the final energy
ENERGY_TEXT = "energy(sigma->0)"

# Line starts for electronic steps in OSZICAR
SCF_LINE_STARTS = ["DAV:", "RMM:", "CG :"]

# INCAR tags written to progress.txt and report.csv
KEY_INCAR_TAGS = ["ENCUT", "EDIFF", "EDIFFG", "NELM", "NSW", "ISIF",
                  "IBRION", "ALGO"]

# ---------------------------------------------------------------
# Error patterns searched in the slurm file and OUTCAR
# Each entry: (text to search for, short label for the report)
# Order matters: the first match wins.
# ---------------------------------------------------------------
# ---------------------------------------------------------------
# Error patterns searched in the slurm file and OUTCAR
# Each entry: (text to search for, short label for the report)
# A list means every text must be on the same line.
# Order matters: the first match wins. Fatal errors come first,
# warnings come last.
# VASP strings are taken from custodian VaspErrorHandler.
# ---------------------------------------------------------------
ERROR_PATTERNS = [
    # Job killed by the scheduler or missing files
    (["file not found", "POTCAR"], "POTCAR missing"),
    ("DUE TO TIME LIMIT", "walltime"),
    ("oom-kill", "out of memory"),
    ("Out Of Memory", "out of memory"),
    ("Allocation would exceed memory limit", "out of memory"),
    ("CANCELLED", "cancelled"),

    # Fatal VASP errors
    ("ZBRENT: fatal error", "zbrent"),
    ("ZBRENT: fatal internal in", "zbrent"),
    ("BRMIX: very serious problems", "brmix"),
    ("Error EDDDAV: Call to ZHEGV failed", "edddav"),
    ("ERROR EDDIAG: Call to routine ZHEEV failed", "zheev"),
    ("ERROR in EDDIAG: call to ZHEEV", "eddiag"),
    ("LAPACK: Routine ZPOTRF failed", "zpotrf"),
    ("Routine ZPOTRF ZTRTRI", "zpotrf"),
    ("ERROR in subspace rotation PSSYEVX", "pssyevx"),
    ("ERROR in subspace rotation PDSYEVX", "pdsyevx"),
    ("EDWAV: internal error, the gradient is not orthogonal",
     "grad not orth"),
    ("REAL_OPTLAY: internal error", "real optlay"),
    ("REAL_OPT: internal ERROR", "real optlay"),
    ("ERROR RSPHER", "rspher"),
    ("TOO FEW BANDS", "too few bands"),
    ("number of bands is not sufficient", "too few bands"),
    ("BRIONS problems: POTIM should be increased", "brions"),
    ("internal error in subroutine PRICEL", "pricel"),
    ("PRICELV: current lattice and primitive lattice are incommensurate",
     "pricelv"),
    ("rotation matrix was not found (increase SYMPREC)", "inv rot mat"),
    ("Found some non-integer element in rotation matrix", "rot matrix"),
    ("group operation missing", "point group"),
    ("Inconsistent Bravais lattice", "bravais lattice"),
    ("ERROR: the triple product of the basis vectors", "triple product"),
    ("Could not get correct shifts", "incorrect shift"),
    ("Fatal error detecting k-mesh", "ksymm"),
    ("Fatal error: unable to match k-point", "ksymm"),
    ("HNFORM: k-point generating", "hnform"),
    ("Tetrahedron method fails", "tet"),
    ("tetrahedron method fails", "tet"),
    ("Routine TETIRR needs special values", "tetirr"),
    ("ERROR: SBESSELITER : nicht konvergent", "nicht konv"),
    ("One of the lattice vectors is very long (>50 A), but AMIN", "amin"),
    ("internal error in SET_CORE_WF", "set core wf"),
    ("while reading WAVECAR", "wavecar read"),
    ("Error reading item", "read error"),
    ("internal error in GENERATE_KPOINTS_TRANS", "kpoints trans"),
    ("RHOSYG", "rhosyg"),
    ("POSMAP", "posmap"),

    # Generic messages, after the specific ones
    ("internal error in subroutine", "internal error"),
    ("VERY BAD NEWS", "very bad news"),

    # Warnings: a run can still finish with these
    ("Sub-Space-Matrix is not hermitian", "subspace hermitian"),
    ("WARNING in EDDRMM: call to ZHEGV failed", "eddrmm"),
    ("DENTET", "dentet"),
]

# ---------------------------------------------------------------
# Status labels used in reports and progress.txt
# ---------------------------------------------------------------
STATUS_RUNNING = "running or pending"
STATUS_NOT_SUBMITTED = "not submitted"
STATUS_MISSING_INPUTS = "missing inputs"
STATUS_CRASHED = "crashed"
STATUS_INCOMPLETE = "incomplete"
STATUS_SCF_NOT_CONVERGED = "SCF not converged"
STATUS_IONIC_NOT_CONVERGED = "ionic not converged"
STATUS_CONVERGED = "converged"

# ---------------------------------------------------------------
# Report groups. Each entry: (group name, list of statuses)
# The order here is the order in the report.
# Must stay below the status labels.
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
# Report folder naming
# ---------------------------------------------------------------
# Month names used in report folder names
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "June",
               "July", "Aug", "Sept", "Oct", "Nov", "Dec"]

# ---------------------------------------------------------------
# Resubmission
# ---------------------------------------------------------------
# Largest number of jobs submitted in one run of resubmit.py
MAX_SUBMIT = 1000

# Largest number of my jobs allowed in the queue at once.
# Set to 0 to turn this limit off.
QUEUE_LIMIT = 15

# ---------------------------------------------------------------
# Relaxation restart
# ---------------------------------------------------------------
# Error labels where CONTCAR is still safe to reuse
CONTCAR_RESTART_LABELS = ["walltime", "zbrent"]
DEFAULT_EDIFF = 1E-4

# ---------------------------------------------------------------
# ZBRENT near minimum check
# ---------------------------------------------------------------
# Error label that triggers the force and energy check
ZBRENT_LABEL = "zbrent"
# Text on the OUTCAR line that holds the stress tensor in kB
STRESS_TEXT = "in kB"

# Largest stress component accepted as relaxed, in kB
STRESS_LIMIT_KB = 1.0

# Text in OUTCAR above each force block
FORCE_BLOCK_TEXT = "TOTAL-FORCE (eV/Angst)"

# Report folders start with this text. scan.py skips them.
REPORT_PREFIX = "report_"
