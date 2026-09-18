# vasp_triage

Tool for VASP jobs on SLURM.

## What this repository is
Python scripts that scan calculation folders, classify job status,
write reports, archive runs, edit INCAR and KPOINTS, and submit jobs.
agent.py is the entry point. See NOTES.md for the design.

## Rules
- Never run sbatch, scancel, or resubmit.py without asking me first.
- Never edit or delete files inside calculation folders.
- Calculation folders live outside this repository. Read them only.
- Use agent.py commands. Do not write new scripts unless I ask.
- Do not run find, grep -r, or du on $SCRATCH or $CFS.
- Ask before any command that takes more than a few seconds.

## Code style
Standard library only. Lines of 80 characters or fewer.
Plain readable logic. No speed optimizations.
Change only what I asked for. Leave the rest of the file alone.
