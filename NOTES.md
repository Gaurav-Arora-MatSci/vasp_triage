# vasp_triage status

Version: v0.1.0, pilot tested on Augie with six cases.

## Modules
config.py    settings, error patterns, statuses, limits
scan.py      find calculation folders, check missing inputs
parse.py     read INCAR, KPOINTS, OUTCAR, OSZICAR, slurm files
classify.py  status rules, SCF and ionic checks, ZBRENT force and stress note
report.py    grouped CSV files and report.md in dated folders
history.py   archive runs as name-N, write progress.txt
edit.py      change INCAR and KPOINTS, filters by status, group, list, where
resubmit.py  sbatch with CONTCAR restart, warnings, max and queue limits
agent.py     one entry point: status, report, history, edit, submit
## Status orderi
running, missing inputs or not submitted, crashed or incomplete,
SCF not converged, ionic not converged, converged

## Key decisions
Energy is energy(sigma->0). One job script: submit_vasp.sh.
Slurm output: slurm-%j.out, no separate error file.
CONTCAR restart for ionic not converged, walltime, zbrent.
ZBRENT note checks forces, energy change, and stress for ISIF >= 3.
MAX_SUBMIT per run, QUEUE_LIMIT total in queue.
Short names for long paths come from working_dirs_list.txt.
## Not done
agent.py, README.md, LLM layer on Stampede3 inside idev,
error patterns and stress limit tuned from real runs.

## Clusters
Augie: AI APIs blocked. Stampede3: API reachable, AI tools on compute
nodes only per TACC policy.

## Clusters
Stampede3: main cluster. API reachable on login and compute nodes.
TACC policy: AI tools on compute nodes only, start with idev.
Plain scripts are not AI tools, so the login node is fine for a small tree.
Augie: AI APIs blocked. Pilot tested here.
NERSC Perlmutter: API reachable. Agents allowed from login nodes, but
no find or recursive searches on large trees.

POTCAR check: element order in POTCAR against POSCAR line 6.
Consistency: ENCUT, EDIFF, EDIFFG, KPOINTS, POTCAR compared within
each parent folder. Both appear at the end of report.md.
Error patterns taken from custodian VaspErrorHandler.
agent_log.txt in the root folder records each command and its output.
Reports are written in the root folder.

## Vtriage running from any folder
vtriage is a launcher script. Add the repository folder to PATH, then
run vtriage from any directory. Without a folder argument, the current
folder is used as the root.
Paths: Perlmutter /global/homes/g/garora/vasp_triage
       Stampede3 check whether the copy is in HOME or WORK
