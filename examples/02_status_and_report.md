# 2. Status, list, report, history

All commands work on the folder you stand in. Give a path or a short
name to work elsewhere, for example vtriage status test.

## Status

```
cd /scratch/user/vt_test
vtriage status
```

After the test campaign ran, with some failures added on purpose:

```
$ vtriage status
Jobs from this folder: 0

All my jobs in the queue: 3
  running: 3
  free slots under limit 15: 12

Folders under /scratch/user/vt_test: 10
  converged: 5
  crashed after reaching accuracy: 1
  SCF not converged: 1
  ionic not converged: 2
  crashed: 1

Needs a look:
  /scratch/user/vt_test/C44/x [SCF at NELM]
```

The statuses, checked in this order:

| Status | Meaning |
|---|---|
| running or pending | the folder is in the SLURM queue |
| missing inputs | no output yet and an input file is missing |
| not submitted | no output yet, all inputs present |
| crashed after reaching accuracy | the relaxation met EDIFFG, then the job died |
| crashed | the job died with a known error message |
| incomplete | the job died with no known message, look at it |
| SCF not converged | the last electronic loop hit NELM above EDIFF |
| ionic not converged | NSW greater than 0 and EDIFFG not met |
| converged | finished cleanly |

They are grouped like this, and the groups are used by --group:

| Group | Statuses |
|---|---|
| converged | converged |
| almost_converged | crashed after reaching accuracy |
| not_converged | SCF not converged, ionic not converged |
| failed | crashed, incomplete |
| other | running or pending, not submitted, missing inputs |

Needs a look lists folders whose last SCF hit NELM, and ZBRENT
crashes that look relaxed.

## List folders with their error lines

In the menu, choose 2, then the group or status to see:

```
$ vtriage menu

What would you like to do?
  1) status summary
  2) list folders by status
  3) write report
  4) archive finished runs
  5) submit jobs
  6) edit INCAR or KPOINTS
  7) activity log
  8) change the root folder
  0) back
Choice: 2

Which folders would you like to see?
  1) everything
  2) group: converged
  3) group: almost_converged
  4) group: not_converged
  5) group: failed
  6) group: other
  7) status: converged
  8) status: crashed after reaching accuracy
  9) status: SCF not converged
  10) status: ionic not converged
  11) status: crashed
  12) status: incomplete
  13) status: running or pending
  14) status: not submitted
  15) status: missing inputs
  0) back
Choice: 1

converged | /scratch/user/vt_test/C11/1 | -25.9513 eV
converged | /scratch/user/vt_test/C11/2 | -25.9513 eV
converged | /scratch/user/vt_test/C11/3 | -25.9513 eV
converged | /scratch/user/vt_test/C11/4 | -25.9513 eV
crashed after reaching accuracy | /scratch/user/vt_test/C11/5
    slurm-59675005.out: slurmstepd: error: *** JOB 59675005 ON nid004001 CANCELLED AT 2026-10-11T15:40:00 DUE TO TIME LIMIT ***
crashed | /scratch/user/vt_test/C11/6
    slurm-59675006.out: error: Detected 2 oom_kill events in StepId=59675006.0.
ionic not converged | /scratch/user/vt_test/C12/1 | -25.9 eV
ionic not converged | /scratch/user/vt_test/C12/2 | -25.9 eV
SCF not converged | /scratch/user/vt_test/C44/x | -25.9 eV
    last SCF hit NELM
converged | /scratch/user/vt_test/C44/y | -25.9513 eV

Folders listed: 10
Save these paths to a list file? y or n: y
File name: all_folders.txt
Written: /scratch/user/vt_test/all_folders.txt
```

The saved file can drive submit or edit with --list. See
03_select_folders_by_path.md.

## Report

```
vtriage report
```

```
$ vtriage report
Directories: 10
Files written:
  /scratch/user/vt_test/report_11_Oct_26_3_41PM_2/report_all.csv
  /scratch/user/vt_test/report_11_Oct_26_3_41PM_2/report_converged.csv
  /scratch/user/vt_test/report_11_Oct_26_3_41PM_2/report_almost_converged.csv
  /scratch/user/vt_test/report_11_Oct_26_3_41PM_2/report_not_converged.csv
  /scratch/user/vt_test/report_11_Oct_26_3_41PM_2/report_failed.csv
  /scratch/user/vt_test/report_11_Oct_26_3_41PM_2/report_other.csv
  /scratch/user/vt_test/report_11_Oct_26_3_41PM_2/report.md
```

Each report goes into a new dated folder, so old reports are kept.
The start of report.md:

```
# VASP job report

Generated: 2026-10-11 15:41
Total directories: 10

## Summary

| Group | Status | Count |
|---|---|---|
| converged | converged | 5 |
| almost_converged | crashed after reaching accuracy | 1 |
| not_converged | SCF not converged | 1 |
| not_converged | ionic not converged | 2 |
| failed | crashed | 1 |
...
```

The first lines of report_all.csv:

```
path,status,energy_sigma0_eV,job_id,ENCUT,EDIFF,EDIFFG,NELM,kpoints_scheme,kpoints_mesh,missing_files,message_label,message_file,message_line,scf_at_nelm,zbrent_note,potcar_labels,potcar_ok,relax_done
/scratch/user/vt_test/C11/1,converged,-25.9513,59675001,350,1E-05,-1E-03,200,Gamma,1 1 1,,,,,False,,W,True,False
```

report.md also holds a POTCAR check and a settings consistency check
across folders in the same parent.

## History: archive finished runs

```
vtriage history
```

```
$ vtriage history
Archived as run 1: /scratch/user/vt_test/C11/1
Archived as run 1: /scratch/user/vt_test/C11/2
...
Archived as run 1: /scratch/user/vt_test/C44/y

Summary:
  archived: 10
```

Each finished run is copied to NAME-1, NAME-2, and so on, and a block
is added to progress.txt in that folder:

```
$ cat C11/6/progress.txt
Run 1 | 11 Oct 2026 3:41 PM | Job 59675006
  ENCUT: 350
  EDIFF: 1E-05
  EDIFFG: -1E-03
  NELM: 200
  NSW: 0
  ISIF: 3
  IBRION: 1
  ALGO: Fast
  KPOINTS: Gamma 1 1 1
  Result: crashed
  energy(sigma->0): not available
  Message: out of memory (slurm-59675006.out): error: Detected 2 oom_kill events in StepId=59675006.0.
  Archived as: INCAR-1 KPOINTS-1 POSCAR-1 OUTCAR-1 OSZICAR-1

$ ls C11/6
INCAR  INCAR-1  KPOINTS  KPOINTS-1  OSZICAR  OSZICAR-1  OUTCAR  OUTCAR-1
POSCAR  POSCAR-1  POTCAR  progress.txt  slurm-59675006.out  submit_vasp.sh
```

You do not need to run history by hand before a resubmit. submit and
edit archive each folder first. A folder that never ran has nothing
to archive, so progress.txt appears only after its first run is
archived.

## The command log

Every command run on a folder, including menu actions and cancelled
previews, is added to agent_log.txt in that folder:

```
======================================================================
2026-10-11 15:40 | python3 agent.py status
Result: checked

Jobs from this folder: 1
  running: 1
...
```

The auto agent writes here only when it submits or finishes.
