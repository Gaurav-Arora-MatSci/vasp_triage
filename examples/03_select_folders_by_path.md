# 3. Submit chosen folders

Submit always takes exactly one way of choosing folders:

| Option | Chooses |
|---|---|
| --status "not submitted" | every folder with that status |
| --group failed | every folder in that group |
| --list file.txt | the folders named in a text file, one per line |

Then --path narrows the choice to exact folders. Nothing is
submitted until you type yes.

## Path patterns

A pattern is compared with the last folder names of each path, one
whole name at a time.

| Pattern | Selects |
|---|---|
| C11/2 | only the folder C11/2, not the folders below it |
| C11/* | every folder directly inside C11 |
| C11/{2..4} | C11/2, C11/3, C11/4 |
| C11/{2,5} | C11/2 and C11/5 |
| C11/{01..10} | C11/01 to C11/10, leading zeros kept |
| */1 | every folder named 1, one level down, in any parent |
| /full/path/C11/6 | exactly that folder |

Rules:

- A star stands for one whole folder name. It never crosses a slash.
- Use two dots for a range: {2..4}, not {2--4}.
- Matching is case sensitive: c11 does not match C11.
- C11 alone matches only a folder named C11 that is itself a
  calculation. To get the folders inside it, write C11/*.
- The same tail can exist in several branches, for example
  1-SQS/strain_calcs/C11_C12_I/* and 2-MEC/strain_calcs/C11_C12_I/*.
  Add a parent name to choose one: 2-MEC/strain_calcs/C11_C12_I/*.
- C11_C12_I/* does not match C11_C12_II.
- On the command line, put each pattern in quotes, or bash changes
  the stars and braces before vtriage sees them. In the menu, type
  them without quotes.
- Several patterns: list them after one --path, or repeat --path.

## Every pattern, tried on the test tree

Each run was answered no.

```
$ vtriage submit --status "not submitted" --path "C11/2"
Jobs in queue: 2 of limit 15
Path filter kept 1 of 10 folders.

Folders to submit: 1
  /scratch/user/vt_test/C11/2
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

```
$ vtriage submit --status "not submitted" --path "C11/*"
Jobs in queue: 2 of limit 15
Path filter kept 6 of 10 folders.

Folders to submit: 6
  /scratch/user/vt_test/C11/1
  /scratch/user/vt_test/C11/2
  /scratch/user/vt_test/C11/3
  /scratch/user/vt_test/C11/4
  /scratch/user/vt_test/C11/5
  /scratch/user/vt_test/C11/6
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

```
$ vtriage submit --status "not submitted" --path "C11/{2..4}"
Jobs in queue: 2 of limit 15
Path filter kept 3 of 10 folders.

Folders to submit: 3
  /scratch/user/vt_test/C11/2
  /scratch/user/vt_test/C11/3
  /scratch/user/vt_test/C11/4
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

```
$ vtriage submit --status "not submitted" --path "C11/{2,5}"
Jobs in queue: 2 of limit 15
Path filter kept 2 of 10 folders.

Folders to submit: 2
  /scratch/user/vt_test/C11/2
  /scratch/user/vt_test/C11/5
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

```
$ vtriage submit --status "not submitted" --path "C44/*"
Jobs in queue: 2 of limit 15
Path filter kept 2 of 10 folders.

Folders to submit: 2
  /scratch/user/vt_test/C44/x
  /scratch/user/vt_test/C44/y
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

Two patterns at once:

```
$ vtriage submit --status "not submitted" --path "C11/1" "C12/*"
Jobs in queue: 2 of limit 15
Path filter kept 3 of 10 folders.

Folders to submit: 3
  /scratch/user/vt_test/C11/1
  /scratch/user/vt_test/C12/1
  /scratch/user/vt_test/C12/2
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

The same name under different parents:

```
$ vtriage submit --status "not submitted" --path "*/1"
Jobs in queue: 2 of limit 15
Path filter kept 2 of 10 folders.

Folders to submit: 2
  /scratch/user/vt_test/C11/1
  /scratch/user/vt_test/C12/1
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

A full path:

```
$ vtriage submit --status "not submitted" --path "/scratch/user/vt_test/C11/6"
Jobs in queue: 2 of limit 15
Path filter kept 1 of 10 folders.

Folders to submit: 1
  /scratch/user/vt_test/C11/6
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

A typo is named, and the other pattern still works:

```
$ vtriage submit --status "not submitted" --path "C99/1" "C11/1"
Jobs in queue: 2 of limit 15
No selected folder matches: C99/1
Path filter kept 1 of 10 folders.

Folders to submit: 1
  /scratch/user/vt_test/C11/1
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

A parent name alone selects nothing, because C11 itself has no INCAR:

```
$ vtriage submit --status "not submitted" --path "C11"
Jobs in queue: 2 of limit 15
No selected folder matches: C11
Path filter kept 0 of 10 folders.
No folders selected.
```

Combining two needs, such as folders 2 to 4 in C11 and 3 to 4 in
C22, is one command:

```
vtriage submit --status "not submitted" --path "C11/{2..4}" "C22/{3,4}"
```

## Limit how many are submitted

--max keeps only the first N of the chosen folders:

```
$ vtriage submit --status "not submitted" --path "C11/*" --max 2
Jobs in queue: 2 of limit 15
Path filter kept 6 of 10 folders.

Folders to submit: 2
  /scratch/user/vt_test/C11/1
  /scratch/user/vt_test/C11/2
Not submitted now because of the limits: 4
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

--queue-limit N stops when you have N jobs in the queue in total.
The smaller of the two limits wins. --queue-limit 0 turns the queue
limit off. If fewer folders are ready than the limits allow, all
ready folders are submitted.

## Submit for real

```
$ vtriage submit --status "not submitted" --path "C11/1"
Jobs in queue: 2 of limit 15
Path filter kept 1 of 10 folders.

Folders to submit: 1
  /scratch/user/vt_test/C11/1
Type yes to save each run and submit: yes
Submitted job 59675001: /scratch/user/vt_test/C11/1

Submitted: 1
```

Check it:

```
$ squeue -u $USER
$ vtriage status
Jobs from this folder: 1
  running: 1

All my jobs in the queue: 3
  running: 3
  free slots under limit 15: 12

Folders under /scratch/user/vt_test: 10
  running or pending: 1
  not submitted: 9
```

The same command again finds nothing, because C11/1 is now running
or pending, not not submitted:

```
$ vtriage submit --status "not submitted" --path "C11/1"
Jobs in queue: 4 of limit 15
No selected folder matches: C11/1
Path filter kept 0 of 9 folders.
No folders selected.
```

A folder that is in the queue is never submitted twice. With --group
or --list it is shown as Running, skipped.

## Submit from a list file

Make the file by hand, or save it from the menu list (see
02_status_and_report.md):

```
$ cat my_list.txt
/scratch/user/vt_test/C11/5
/scratch/user/vt_test/C11/6

$ vtriage submit --list my_list.txt
Jobs in queue: 4 of limit 15

Folders to submit: 2
  /scratch/user/vt_test/C11/5
  /scratch/user/vt_test/C11/6
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

A list and a path together:

```
$ vtriage submit --list my_list.txt --path "C11/6"
Jobs in queue: 4 of limit 15
Path filter kept 1 of 2 folders.

Folders to submit: 1
  /scratch/user/vt_test/C11/6
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

Empty lines and lines starting with # are ignored in the list file.

## Resubmit failed folders

After the jobs ran, by group or by status:

```
$ vtriage submit --group failed
Jobs in queue: 3 of limit 15

Folders to submit: 1
  /scratch/user/vt_test/C11/6
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

Warnings you may see before the yes:

```
$ vtriage submit --status "SCF not converged"
Jobs in queue: 3 of limit 15
Warning: last SCF hit NELM. Fix NELM or ALGO first: /scratch/user/vt_test/C44/x

Folders to submit: 1
  /scratch/user/vt_test/C44/x
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

```
$ vtriage submit --group almost_converged
Jobs in queue: 3 of limit 15
Note: reached required accuracy before the job died. Fix the cause, then this should finish quickly: /scratch/user/vt_test/C11/5
CONTCAR missing or empty, skipped: /scratch/user/vt_test/C11/5
Nothing to submit.
```

Unfinished relaxations, walltime kills, and ZBRENT crashes restart
from CONTCAR. CONTCAR is copied to POSCAR only after its element
line and atom counts match POSCAR. Here CONTCAR was missing, so the
folder was skipped rather than restarted from the wrong structure.

Other warnings:

- Warning: same error as previous run (label). Change settings
  first. The folder crashed twice with the same error.
- Warning: ZBRENT: fatal error in bracketing, followed by the forces
  and stress against EDIFFG. Add --skip-zbrent-met to skip those
  that look relaxed.

Converged folders are skipped unless you add --force:

```
$ vtriage submit --group converged --force --path "C11/2"
Jobs in queue: 3 of limit 15
Path filter kept 1 of 5 folders.

Folders to submit: 1
  /scratch/user/vt_test/C11/2
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

## Errors that stop the command

```
$ vtriage submit --path "C11/*"
Error: give exactly one of --status, --group, or --list.
```

```
$ vtriage submit --status crashed --yes
Error: --yes works only with --status "not submitted".
```

--yes skips the question. It exists for the auto agent and is only
allowed for new jobs, so a failed run is never resubmitted without
you looking at it.

## The same in the menu

Choose 5, then the status, then 2 for path patterns. The typed
answers are shown after each Choice.

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
Choice: 5

Which folders?
  1) group: converged
  2) group: almost_converged
  3) group: not_converged
  4) group: failed
  5) group: other
  6) status: converged
  7) status: crashed after reaching accuracy
  8) status: SCF not converged
  9) status: ionic not converged
  10) status: crashed
  11) status: incomplete
  12) status: running or pending
  13) status: not submitted
  14) status: missing inputs
  15) from a list file
  0) back
Choice: 13

Anything else?
  1) submit now
  2) only folders matching a path pattern
  3) set the number of jobs per run
  4) set the queue limit
  5) also submit converged folders
  6) skip ZBRENT folders that look relaxed
  0) back
Choice: 2

Path patterns, matched against the last folder names:
  C11/2        only the folder C11/2
  C11/*        every folder directly inside C11
  C11/{2..10}  C11/2 to C11/10
  C11/{2,5}    C11/2 and C11/5
Separate several patterns with spaces.
Patterns: C11/{2,5} C44/*
So far: --status not submitted --root /scratch/user/vt_test --path=C11/{2,5} --path=C44/*

Anything else?
  1) submit now
  2) only folders matching a path pattern
  3) set the number of jobs per run
  4) set the queue limit
  5) also submit converged folders
  6) skip ZBRENT folders that look relaxed
  0) back
Choice: 1

Running: vtriage submit --status not submitted --root /scratch/user/vt_test --path=C11/{2,5} --path=C44/*

Jobs in queue: 2 of limit 15
Path filter kept 4 of 10 folders.

Folders to submit: 4
  /scratch/user/vt_test/C11/2
  /scratch/user/vt_test/C11/5
  /scratch/user/vt_test/C44/x
  /scratch/user/vt_test/C44/y
Type yes to save each run and submit: no
Cancelled. Nothing submitted.
```

The path option is not on the main menu. It appears after you pick
submit and a status. Options 3 to 6 work the same way: each one adds
to the So far line, and 1 runs it.
