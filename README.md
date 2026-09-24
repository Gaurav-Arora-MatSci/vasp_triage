# vasp_triage

```
 ================================================================
  __     ___    ____  ____    _____ ____  ___    _    ____ _____
  \ \   / / \  / ___||  _ \  |_   _|  _ \|_ _|  / \  / ___| ____|
   \ \ / / _ \ \___ \| |_) |   | | | |_) || |  / _ \| |  _|  _|
    \ V / ___ \ ___) |  __/    | | |  _ < | | / ___ \ |_| | |___
     \_/_/   \_\____/|_|       |_| |_| \_\___/_/   \_\____|_____|
 ================================================================
```

Scan thousands of VASP directories, find out what happened in each
one, record the history inside the directory, fix the inputs, and
resubmit. Standard library Python only. Nothing to install.

Built for the situation every DFT campaign ends up in: several
hundred directories on scratch, made over months, some finished, some
crashed, some never submitted, and no memory of which is which.

## Install

```bash
git clone https://github.com/USER/vasp_triage.git
export PATH=$PWD/vasp_triage:$PATH
```

Add the export line to your `~/.bashrc` to keep it. No pip, no conda,
no database, no network. Python 3.5 or newer, and SLURM.

## Use

```bash
cd /path/to/my/calculations
vtriage status
```

```
My jobs in the queue: 15
  pending: 12
  running: 3
  free slots under limit 15: 0

Folders under /scratch/BCC: 60
  converged: 41
  crashed after reaching accuracy: 1
  SCF not converged: 2
  crashed: 3
  running or pending: 13

Needs a look:
  /scratch/BCC/W20_3 [SCF at NELM]
  /scratch/BCC/W30_1 [ZBRENT, criteria met]
```

Every command takes the current folder as its root, so you can just
`cd` and go. A guided menu is there if you prefer it:

```bash
vtriage menu
```

## The commands

| Command | Does |
|---|---|
| `vtriage status` | counts by job state and folder status |
| `vtriage report` | CSV files plus report.md in a dated folder |
| `vtriage history` | archive finished runs, write progress.txt |
| `vtriage edit` | change INCAR and KPOINTS, with a preview |
| `vtriage submit` | sbatch, with limits and safety checks |
| `vtriage menu` | all of the above, numbered |

Pick folders by status, by group, or from a list file:

```bash
vtriage edit --group not_converged --set NELM=200
vtriage edit --list crashed.txt --set EDIFF=1E-6 --kpoints mp 4 4 4
vtriage submit --status "not submitted" --max 10
vtriage submit --group failed --skip-zbrent-met
```

The menu can list every folder in a given status, with its error
lines, and save those paths to a file that `--list` then reads. So
finding the broken runs and acting on exactly those is two steps.

Nothing is changed or submitted until you type yes.

## Status rules

Checked in this order, because the order is what makes the answer
correct:

1. in the SLURM queue, by working directory
2. no output at all, so not submitted, or missing inputs
3. no timing block in OUTCAR, so the run did not finish:
   - the required accuracy line is present, so crashed after
     reaching accuracy
   - a known error message, so crashed
   - neither, so incomplete
4. last electronic loop hit NELM, so SCF not converged
5. NSW greater than 0 without the required accuracy line, so ionic
   not converged
6. converged

An ionic criterion met with an unconverged electronic loop is not
convergence, and the tool says so. When the electronic loop ends
exactly at NELM, the dE and d eps of the final step are compared with
EDIFF rather than assuming failure.

## What it catches that a status alone does not

**POTCAR order.** A POTCAR whose elements do not match the POSCAR
runs to completion and gives a meaningless number. No crash, no
warning. Checked for every folder, including ones not yet submitted.

**Settings drift.** Within each parent folder, ENCUT, EDIFF, EDIFFG,
the k mesh, and the POTCAR labels are compared across all
calculations. Catches the quiet disaster of a composition series
where one point was recomputed months later with a different cutoff.

**A failure that is really a finished structure.** When VASP stops
with a ZBRENT bracketing error, the last force block and the stress
tensor are read and reported against EDIFFG. A structure sitting at
its minimum, where the optimizer has nothing left to do, is not the
same as one that genuinely failed. Other tools just retry.

**A relaxation that met EDIFFG before the job died.** Out of memory
and walltime kills often land just after the ionic loop converged.
Those get their own status and their own group in the report, instead
of being lumped in with real crashes, and they restart from CONTCAR.

**A fix that did not work.** If a folder crashes twice with the same
error, you are warned before the third attempt.

**Restarts.** Unfinished relaxations, walltime kills, and ZBRENT
crashes are restarted from CONTCAR, but only after the element list
is checked against POSCAR.

Error message strings are taken from custodian's `VaspErrorHandler`,
so the coverage is the community's, not one person's guesses.

## Version control for your calculations

Every archived run copies INCAR, KPOINTS, POSCAR, CONTCAR, OUTCAR,
and OSZICAR to `NAME-N`, and appends a block to `progress.txt` in
that directory:

```
Run 1 | 17 Sept 2026 9:51 AM | Job 316683
  ENCUT: 350
  EDIFF: 1E-04
  EDIFFG: -1E-03
  NELM: 3
  KPOINTS: Gamma 1 1 1
  Result: crashed
  energy(sigma->0): not available
  Message: zbrent: ZBRENT: fatal error in bracketing
  Archived as: INCAR-1 KPOINTS-1 POSCAR-1 CONTCAR-1 OUTCAR-1 OSZICAR-1

  Next run starts from CONTCAR

Run 2 | 17 Sept 2026 11:30 AM | Job 316703
  ENCUT: 350
  EDIFF: 1E-06
  EDIFFG: -1E-02
  NELM: 60
  KPOINTS: Gamma 1 1 1
  Result: converged
  energy(sigma->0): -696.30022286 eV
  Message: none
  Archived as: INCAR-2 KPOINTS-2 POSCAR-2 CONTCAR-2 OUTCAR-2 OSZICAR-2
```

Read that as a commit history, because that is what it is. Each run
is a commit, the settings are the diff, the result is the message,
and the archived files are the real tree at that point.

Which means you can answer, months later, exactly which settings
produced a given number. Not roughly, not from memory. The INCAR
sits beside the energy it produced.

The history is plain text in the directory it describes, so it
travels with the data. Copy the folder to a collaborator or into
supplementary material and the whole history goes too. Read it with
`cat`. No tool required.

A second log, `agent_log.txt`, is written in the campaign root with
every command you ran and what it printed.

## How it differs from custodian, atomate2, and AiiDA

Those tools own the run. You start inside them and stay there, and in
exchange you get supervision, workflows, and a provenance database.
They are good software and worth using for a managed campaign.

vasp_triage starts from the file system instead. Any directory with
an INCAR is a calculation, whether it was made by a bash loop, by
VASPKIT, by a colleague, or by an earlier version of your own
pipeline. It installs nothing, needs no network, and never acts
without your yes.

The two mix perfectly well: custodian fixing runs while they happen,
vasp_triage recording and triaging what came out.

## Limits

- It does not supervise a running job, so it cannot fix errors mid
  run the way custodian does.
- Provenance is per directory, not a graph across derived quantities.
- Unknown errors appear as `incomplete`, which tells you to look
  rather than telling you why.
- One calculation per directory, with a consistently named job
  script. That assumption is what keeps it simple.
- Written against SLURM.

## Layout

```
config.py     settings, error patterns, statuses, limits
scan.py       find calculation folders, check missing inputs
parse.py      read INCAR, KPOINTS, POTCAR, OUTCAR, OSZICAR, SLURM
classify.py   status rules, SCF and ionic checks, POTCAR check
report.py     grouped CSV files and report.md
history.py    archive runs, write progress.txt
edit.py       change INCAR and KPOINTS
resubmit.py   sbatch with checks and limits
agent.py      entry point, command log
menu.py       numbered menu
vtriage       launcher
```

Every file is plain, readable Python with no dependencies. Change it
in minutes. That is the point.

## Feedback wanted

Run `vtriage status` on an old directory tree and send me any folder
it marks `incomplete`, together with the last lines of its SLURM
file. Those are the error strings the pattern list is still missing,
and they are the single most useful thing you can contribute.

Issues and discussions are open.

## Citation

If this saved you time, cite the release DOI.

## License

MIT.