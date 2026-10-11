# 4. Edit INCAR and KPOINTS

edit chooses folders the same way as submit: exactly one of
--status, --group, --list, then optional --path and --where. Then at
least one change:

| Option | Does |
|---|---|
| --set TAG=VALUE | change a tag, or add it if missing; repeat for more tags |
| --remove TAG | delete a tag; repeat for more |
| --kpoints gamma N1 N2 N3 | write a new Gamma centred mesh |
| --kpoints mp N1 N2 N3 | write a new Monkhorst Pack mesh |
| --where TAG=VALUE | only folders whose INCAR has that value |

Every change is shown first. Nothing is written until you type yes.
Before writing, each folder's current run is archived, if it has
one. Running or pending folders are skipped. Comments in INCAR stay.

## Set a tag in chosen folders

```
$ vtriage edit --status "not submitted" --path "C11/{3,4}" --set NELM=80
Path filter kept 2 of 10 folders.

/scratch/user/vt_test/C11/3
  NELM: 200 -> 80

/scratch/user/vt_test/C11/4
  NELM: 200 -> 80

Folders to change: 2
Type yes to save each run and apply the changes: yes
Changed: /scratch/user/vt_test/C11/3
Changed: /scratch/user/vt_test/C11/4

$ grep NELM C11/3/INCAR
NELM = 80
```

Folders that already have the value are reported, not changed:

```
$ vtriage edit --status "not submitted" --path "C11/*" --set NELM=80
Path filter kept 6 of 10 folders.

/scratch/user/vt_test/C11/1
  NELM: 200 -> 80

/scratch/user/vt_test/C11/2
  NELM: 200 -> 80
No change needed: /scratch/user/vt_test/C11/3
No change needed: /scratch/user/vt_test/C11/4

/scratch/user/vt_test/C11/5
  NELM: 200 -> 80

/scratch/user/vt_test/C11/6
  NELM: 200 -> 80

Folders to change: 4
Type yes to save each run and apply the changes: no
Cancelled. No files changed.
```

## Remove a tag and set another

```
$ vtriage edit --status "not submitted" --path "C12/*" --remove LREAL --set ALGO=Normal
Path filter kept 2 of 10 folders.

/scratch/user/vt_test/C12/1
  ALGO: Fast -> Normal
  remove LREAL (was .FALSE.)

/scratch/user/vt_test/C12/2
  ALGO: Fast -> Normal
  remove LREAL (was .FALSE.)

Folders to change: 2
Type yes to save each run and apply the changes: no
Cancelled. No files changed.
```

## Change KPOINTS

```
$ vtriage edit --status "not submitted" --path "C44/*" --kpoints mp 2 2 2
Path filter kept 2 of 10 folders.

/scratch/user/vt_test/C44/x
  KPOINTS: Gamma 1 1 1 -> Monkhorst Pack 2 2 2

/scratch/user/vt_test/C44/y
  KPOINTS: Gamma 1 1 1 -> Monkhorst Pack 2 2 2

Folders to change: 2
Type yes to save each run and apply the changes: no
Cancelled. No files changed.
```

When KPOINTS changes, WAVECAR is renamed to WAVECAR_old, since the
old wavefunctions do not fit the new mesh.

## Only folders where a tag has a value

```
$ vtriage edit --group other --where NSW=1 --set EDIFFG=-1E-02
Condition not met, skipped: /scratch/user/vt_test/C11/1
Condition not met, skipped: /scratch/user/vt_test/C11/2
Condition not met, skipped: /scratch/user/vt_test/C11/3
Condition not met, skipped: /scratch/user/vt_test/C11/4
Condition not met, skipped: /scratch/user/vt_test/C11/5
Condition not met, skipped: /scratch/user/vt_test/C11/6

/scratch/user/vt_test/C12/1
  EDIFFG: -1E-03 -> -1E-02

/scratch/user/vt_test/C12/2
  EDIFFG: -1E-03 -> -1E-02
Condition not met, skipped: /scratch/user/vt_test/C44/x
Condition not met, skipped: /scratch/user/vt_test/C44/y

Folders to change: 2
Type yes to save each run and apply the changes: no
Cancelled. No files changed.
```

Case is ignored in --where. A tag missing from INCAR counts as no
match.

## Fix a failed run, then resubmit

The usual pair after an SCF failure:

```
$ vtriage edit --status "SCF not converged" --set ALGO=Normal --set NELM=300

/scratch/user/vt_test/C44/x
  ALGO: Fast -> Normal
  NELM: 200 -> 300

Folders to change: 1
Type yes to save each run and apply the changes: yes

$ vtriage submit --status "SCF not converged"
```

More examples:

```
vtriage edit --group not_converged --set NELM=200
vtriage edit --list crashed.txt --set EDIFF=1E-6 --kpoints mp 4 4 4
vtriage edit --group failed --path "2-MEC/strain_calcs/*/*" --set NELM=200
```

## Error when no change is given

```
$ vtriage edit --status "not submitted" --path "C11/1"
Error: give --set, --remove, or --kpoints.
```

## The same in the menu

Choose 6, then the status, then the steps below. The typed answers
are shown after each prompt.

```
Choice: 6
Which folders? ...
Choice: 13

What should be changed?
  1) set a tag, for example NELM=200
  2) remove a tag
  3) rewrite KPOINTS
  4) only folders where a tag has a value
  5) only folders matching a path pattern
  6) done, show me the preview
  0) back
Choice: 5

Path patterns, matched against the last folder names:
  C11/2        only the folder C11/2
  C11/*        every folder directly inside C11
  C11/{2..10}  C11/2 to C11/10
  C11/{2,5}    C11/2 and C11/5
Separate several patterns with spaces.
Patterns: C11/{3,4}
So far: --path=C11/{3,4}

What should be changed?
  ...
Choice: 1
Tag name, for example EDIFF: NELM
New value for NELM: 80
So far: --path=C11/{3,4} --set NELM=80

What should be changed?
  ...
Choice: 6

Running: vtriage edit --status not submitted --root /scratch/user/vt_test --path=C11/{3,4} --set NELM=80

Path filter kept 2 of 10 folders.

/scratch/user/vt_test/C11/3
  NELM: 200 -> 80

/scratch/user/vt_test/C11/4
  NELM: 200 -> 80

Folders to change: 2
Type yes to save each run and apply the changes: no
Cancelled. No files changed.
```

Choose 1 or 2 again to add more tags before 6. The So far line shows
everything chosen.

## Preparing the test tree with edit

The production INCAR used for the test needed changes for 8 MPI
ranks and one k point. KPAR=14 needs 14 ranks and 14 k points,
NCORE=16 is larger than 8 ranks, LREAL=Auto is not advised for 2
atoms, LCHARGE is not a valid tag, and a 100 step relaxation may not
fit a short test. The tool fixed them in one step:

```
vtriage edit --status "not submitted" --remove KPAR --remove NCORE --remove LCHARGE --set NSW=0 --set EDIFF=1E-05 --set LREAL=.FALSE.
vtriage edit --status "not submitted" --path "C12/*" --set NSW=1 --set IBRION=2
```

The second line makes the C12 folders run one ionic step, so they
end as ionic not converged and show up in the auto agent's list of
folders that need a look.
