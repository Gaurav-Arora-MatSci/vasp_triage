# 5. The auto agent: submit a whole campaign on a schedule

vtriage auto runs one cycle. Run on a schedule, it works through a
campaign on its own and emails you when it is done. It needs no LLM
and no API key. The optional decision agent, which continues
unconverged runs inside the same cycle, is in
[09_decision_agent.md](09_decision_agent.md).

## What one cycle does

1. If AUTO_DONE exists in the folder, it stops at once.
2. If another cycle is still running, it stops at once.
3. If folders are not submitted, it submits up to the batch size,
   without going over the queue limit.
4. If everything was submitted and jobs are still queued, it waits.
5. If everything was submitted once and nothing is queued, it writes
   the final report, writes AUTO_DONE with every folder that needs a
   look, and sends one email.

It only ever submits folders with status not submitted. Crashed and
unconverged folders are listed in AUTO_DONE for you, never
resubmitted.

vtriage auto submits immediately, with no yes prompt. Run it only in
the folder you mean.

## Settings

In local_settings.py in the repo folder:

```
AUTO_BATCH = 20
AUTO_QUEUE_LIMIT = 30
AUTO_EMAIL = "you@example.com"
AUTO_EMAIL_SBATCH_OPTIONS = ["-A", "YOUR_ACCOUNT", "-q", "shared", "-C", "cpu",
                             "-n", "1", "-c", "2", "-t", "1"]
```

On the command line:

| Option | Meaning | Default |
|---|---|---|
| --root FOLDER | campaign folder | the folder you stand in |
| --path PATTERN | only these folders, same patterns as submit | every folder |
| --batch N | new jobs per cycle | AUTO_BATCH |
| --queue-limit N | your jobs allowed in the queue, 0 for no limit | AUTO_QUEUE_LIMIT |

The queue limit counts all your jobs, from every folder and project,
except helper jobs whose name starts with vtriage_. Name the
scheduled job vtriage_auto so it is not counted. With 2 jobs from
another project and a limit of 6, only 4 slots are free.

## Check the email first

Many clusters have no working mail command. On Perlmutter, mail
fails like this and saves the message to ~/dead.letter:

```
$ echo test | mail -s vtriage_test you@example.com
/usr/sbin/sendmail: No such file or directory
"/global/homes/u/user/dead.letter" 9/229
. . . message not sent.
```

Slurm mail does work. Test it with a tiny job:

```
sbatch -A YOUR_ACCOUNT -q shared -C cpu -n 1 -c 2 -t 1 --mail-type=END --mail-user=you@example.com --wrap=hostname
```

If that email arrives, the auto agent email works too. Use the shared
queue, not debug: debug charges a whole node for a job that only
prints a file.

## Run it by hand first

Use a test tree, a small batch, and a small limit, so the batching
is visible:

```
cd /scratch/user/vt_test
vtriage auto --batch 3 --queue-limit 6
```

A full run on the test tree. Two jobs from another project and the
vtriage_auto helper were already in the queue.

First cycle: 3 free slots after the 2 other jobs, batch of 3:

```
$ vtriage auto --batch 3 --queue-limit 6
2026-10-11 15:41 folders: 10, not submitted: 9, in queue: 0

Folders to submit: 3
  /scratch/user/vt_test/C11/2
  /scratch/user/vt_test/C11/3
  /scratch/user/vt_test/C11/4
Not submitted now because of the limits: 6
Confirmed by --yes.
Submitted job 59675002: /scratch/user/vt_test/C11/2
Submitted job 59675003: /scratch/user/vt_test/C11/3
Submitted job 59675004: /scratch/user/vt_test/C11/4

Submitted: 3
Run the same command again later for the next batch.
```

Second cycle: 2 other jobs plus 3 test jobs leave 1 free slot:

```
$ vtriage auto --batch 3 --queue-limit 6
2026-10-11 15:41 folders: 10, not submitted: 6, in queue: 3

Folders to submit: 1
  /scratch/user/vt_test/C11/5
Not submitted now because of the limits: 5
Confirmed by --yes.
Submitted job 59675005: /scratch/user/vt_test/C11/5

Submitted: 1
Run the same command again later for the next batch.
```

Third cycle: the queue is full. The helper job is not counted:

```
$ vtriage auto --batch 3 --queue-limit 6
2026-10-11 15:41 folders: 10, not submitted: 5, in queue: 4
Queue full: 6 of 6. Nothing submitted.

$ squeue -u $USER -h -o "%i %j %T"
59600001 elastic_A RUNNING
59600002 elastic_B RUNNING
59675990 vtriage_auto RUNNING
59675002 test RUNNING
59675003 test RUNNING
59675004 test RUNNING
59675005 test RUNNING
```

After those jobs finished, the next cycles continued:

```
$ vtriage auto --batch 3 --queue-limit 6
2026-10-11 15:41 folders: 10, not submitted: 5, in queue: 0

Folders to submit: 3
  /scratch/user/vt_test/C11/6
  /scratch/user/vt_test/C12/1
  /scratch/user/vt_test/C12/2
Not submitted now because of the limits: 2
Confirmed by --yes.
Submitted job 59675006: /scratch/user/vt_test/C11/6
Submitted job 59675007: /scratch/user/vt_test/C12/1
Submitted job 59675008: /scratch/user/vt_test/C12/2

Submitted: 3
Run the same command again later for the next batch.
```

Fewer folders left than free slots: it submits what is left.

```
$ vtriage auto --batch 3 --queue-limit 6
2026-10-11 15:41 folders: 10, not submitted: 1, in queue: 0

Folders to submit: 1
  /scratch/user/vt_test/C44/y
Confirmed by --yes.
Submitted job 59675010: /scratch/user/vt_test/C44/y

Submitted: 1
```

Everything submitted, one job still queued:

```
$ vtriage auto --batch 3 --queue-limit 6
2026-10-11 15:41 folders: 10, not submitted: 0, in queue: 1
All submitted. Waiting for 1 jobs to leave the queue.
```

The finishing cycle:

```
$ vtriage auto --batch 3 --queue-limit 6
2026-10-11 15:41 folders: 10, not submitted: 0, in queue: 0
Nothing left to submit and nothing in the queue.
Writing the final report.
Directories: 10
Files written:
  /scratch/user/vt_test/report_11_Oct_26_3_41PM/report_all.csv
  /scratch/user/vt_test/report_11_Oct_26_3_41PM/report_converged.csv
  /scratch/user/vt_test/report_11_Oct_26_3_41PM/report_almost_converged.csv
  /scratch/user/vt_test/report_11_Oct_26_3_41PM/report_not_converged.csv
  /scratch/user/vt_test/report_11_Oct_26_3_41PM/report_failed.csv
  /scratch/user/vt_test/report_11_Oct_26_3_41PM/report_other.csv
  /scratch/user/vt_test/report_11_Oct_26_3_41PM/report.md
vasp_triage auto agent finished
Date: 2026-10-11 15:41
Root: /scratch/user/vt_test
Path patterns: none, every folder

Folders: 10
  converged: 8
  ionic not converged: 2

Folders that need a look: 2
  ionic not converged | /scratch/user/vt_test/C12/1
  ionic not converged | /scratch/user/vt_test/C12/2

Email: Submitted batch job 59675011, to you@example.com
```

The same text is saved in AUTO_DONE in the campaign folder:

```
$ cat AUTO_DONE
```

The email subject carries the counts. From the Perlmutter run:

```
perlmutter Slurm Job_id=59676793 Name=vtriage_done_vt_test_9ok_2look Ended, Run time 00:00:03, COMPLETED, ExitCode 0
```

The body is only Slurm accounting. The details are in AUTO_DONE and
vtriage_done.out. A job you cancel by hand shows CANCELLED with zero
run time instead, which is not a fault.

Every later cycle stops at once:

```
$ vtriage auto --batch 3 --queue-limit 6
2026-10-11 15:41 AUTO_DONE found, nothing to do: /scratch/user/vt_test
```

## Safety checks

A cycle that starts while another is still running:

```
$ vtriage auto --batch 3 --queue-limit 6
2026-10-11 15:41 Another auto run is active. Skipped.
```

The lock file auto.lock is removed at the end of each cycle. One
older than 60 minutes is treated as left over from a killed run and
replaced.

No folder matches, for example a typo in --path, or a tree whose
INCAR files were deleted. It refuses to finish, so an empty campaign
is never marked done:

```
$ vtriage auto --root /scratch/user/vt_test --path "C99/*"
2026-10-11 15:41 Error: no calculation folders match. Check --root and --path.
```

The same message appeared on Perlmutter when the test tree had been
reset with the INCAR files removed:

```
2026-10-11 10:45 Error: no calculation folders match. Check --root and --path.
2026-10-11 10:50 Error: no calculation folders match. Check --root and --path.
```

After the inputs were copied back, the next cycle carried on by
itself.

## Only part of a campaign

```
vtriage auto --path "C11/*" "C12/{1,2}"
```

Only those folders are submitted, and AUTO_DONE is written when
those are done.

## Start again

```
rm AUTO_DONE
```

The next cycle picks up any not submitted folders again.

## Run it on a schedule with scrontab (NERSC)

scrontab is the Slurm version of cron. It has nothing to do with
Claude. Open it:

```
scrontab -e
```

An editor opens, usually vi, with a block of comments. Press G to go
to the end, o to start a new line, paste the entry, press Esc, type
:wq and Enter. If the screen shows ^O Write Out at the bottom, it is
nano: paste, then Ctrl+O, Enter, Ctrl+X.

Test entry, every 5 minutes:

```
#SCRON -q cron
#SCRON -A YOUR_ACCOUNT
#SCRON -t 00:05:00
#SCRON -J vtriage_auto
#SCRON -o /scratch/user/vt_test/auto_cron.log
#SCRON --open-mode=append
*/5 * * * * /global/homes/u/user/vasp_triage/vtriage auto --root /scratch/user/vt_test --batch 3 --queue-limit 6
```

- Use the full path to vtriage. scrontab does not read ~/.bashrc.
- Use --root instead of cd.
- -J vtriage_auto keeps the helper out of the queue count.
- Times are UTC.

Check it was saved:

```
$ scrontab -l
# Welcome to scrontab, Slurm's cron-like interface.
...
#SCRON -q cron
#SCRON -A YOUR_ACCOUNT
#SCRON -t 00:05:00
#SCRON -J vtriage_auto
#SCRON -o /scratch/user/vt_test/auto_cron.log
#SCRON --open-mode=append
*/5 * * * * /global/homes/u/user/vasp_triage/vtriage auto --root /scratch/user/vt_test --batch 3 --queue-limit 6

# min hour day-of-month month day-of-week command
```

The helper job waits in the queue between runs:

```
$ squeue -u $USER
59675998      cron vtriage_   user PD       0:00      1 (BeginTime)
```

BeginTime means it waits for its next start time. That is normal.
After each run, Slurm queues it again for the next slot.

Watch it work:

```
tail -f /scratch/user/vt_test/auto_cron.log
```

Each cycle adds one summary line, plus the submit output when it
acts. Ctrl+C stops watching; the schedule keeps running.

To get these steps and the block written for a given folder in plain
English, see Running automatically through Claude in
06_llm_vclaude.md.

## Stop the schedule

When AUTO_DONE is written, the job keeps waking up and exiting until
you remove the entry:

```
scrontab -e
```

In vi, put the cursor on the first #SCRON line, type 7dd, then :wq.
Check with scrontab -l and squeue -u $USER.

## Production schedule

For a real campaign, a longer interval is enough, since each cycle
scans every folder:

```
#SCRON -q cron
#SCRON -A YOUR_ACCOUNT
#SCRON -t 00:10:00
#SCRON -J vtriage_auto
#SCRON -o /pscratch/sd/u/user/campaign/auto_cron.log
#SCRON --open-mode=append
7 */5 * * * /global/homes/u/user/vasp_triage/vtriage auto --root /pscratch/sd/u/user/campaign
```

7 */5 * * * runs at minute 7 of hours 0, 5, 10, 15, and 20 UTC.
Minute 7 avoids the busy start of the hour. The gap across midnight
is 4 hours, not 5.

NERSC comments out scrontab entries when it cancels them, for
example before maintenance. Run scrontab -e and remove the comment
marks to start it again. Long running processes need the workflow
queue, but short cycles like these do not.

## Moving pending jobs under the auto agent

Pending jobs that never started leave no output, so after
scancel JOBID their folders show as not submitted again and the auto
agent picks them up. Cancel by job ID, never with scancel -u $USER,
which also kills running jobs. A folder with output from an earlier
run keeps that run's status instead, and the auto agent leaves it
alone.

## Other clusters

The auto agent uses only sbatch and squeue. Two things depend on the
cluster: how recurring jobs are scheduled, scrontab on NERSC, cron
elsewhere if login node cron is allowed; and whether Slurm mail is
delivered. Test both before relying on them.
