# 8. Schedule a campaign in plain English (NERSC only)

`vtriage schedule` puts the auto agent on scrontab for you. With the
vclaude wrapper, one sentence starts a whole campaign:

```
vclaude "run all jobs in this folder once, check every 10 minutes, 2 jobs per cycle, queue limit 20"
vclaude_yes
```

The first call shows a plan and installs nothing. The second call is
your yes. It installs the plan and submits the first batch at once.
After that, scrontab runs one auto cycle at every interval. When the
campaign is done, you get the email and the entry removes itself.

**This works only on NERSC Perlmutter.** It needs scrontab, the Slurm
cron. TACC Stampede3 has scrontab disabled, so there run
`vtriage auto --root FOLDER` by hand, one cycle at a time.

## 1. Setup, once per machine

1. Check these in `~/vasp_triage/local_settings.py`:

   ```python
   AUTO_EMAIL = "you@example.com"
   AUTO_EMAIL_SBATCH_OPTIONS = ["-A", "YOUR_ACCOUNT", "-q", "shared",
                                "-C", "cpu", "-n", "1", "-c", "2",
                                "-t", "1"]
   ```

   The scrontab job uses the `-A` account from this list. To use a
   different account, add `SCHEDULE_ACCOUNT = "YOUR_ACCOUNT"`. To
   change the interval used when none is given, add
   `SCHEDULE_EVERY = "5h"`.

2. Install the wrappers. Delete any older vclaude block from
   `~/.bashrc` first, then:

   ```
   cat ~/vasp_triage/examples/templates/vclaude.sh >> ~/.bashrc
   source ~/.bashrc
   grep -c "vclaude()" ~/.bashrc
   ```

   The count must be 1.

3. Copy the instructions file:

   ```
   cp ~/vasp_triage/examples/templates/CLAUDE_example.md ~/.claude/CLAUDE.md
   ```

## 2. What you can ask

Run every request from inside the campaign folder. Claude turns your
words into one `vtriage schedule` command and shows the plan.

| You type | Claude runs |
|---|---|
| `vclaude "run all jobs in this folder once, check every 10 minutes, 2 jobs per cycle, queue limit 20"` | `vtriage schedule --every 10m --batch 2 --queue-limit 20` |
| `vclaude "run all jobs in this folder and email me when done"` | `vtriage schedule` (every 5 hours, batch and limit from local_settings.py) |
| `vclaude "submit only the C11 folders, check every hour"` | `vtriage schedule --every 1h --path "C11/*"` |
| `vclaude "run C11 folders 2 to 4 and all of C44, check every 2 hours"` | `vtriage schedule --every 2h --path "C11/{2..4}" "C44/*"` |
| `vclaude "run jobs in this folder with batch size of 20 and checking back again after 3 hours until every job has reached required accuracy"` | `vtriage schedule --every 3h --batch 20 --agent auto` |
| `vclaude "run all jobs, check every hour, show me the agent plan before it acts"` | `vtriage schedule --every 1h --agent ask` |
| `vclaude "run all jobs every 2 hours, only submit"` | `vtriage schedule --every 2h --agent off` |
| `vclaude "run everything, check every 30 minutes, keep at most 10 of my jobs queued"` | `vtriage schedule --every 30m --queue-limit 10` |
| `vclaude "run all jobs, check every 90 minutes"` | nothing; says 90 minutes cannot be a cron interval and offers 1h or 2h |
| `vclaude "stop the automatic run in this folder"` | nothing; prints `vtriage unschedule` for you to run |
| `vclaude_yes` | `vtriage confirm`, only if the previous answer showed a plan |

The first row was recorded on Perlmutter. The other rows show what
the CLAUDE.md rules tell Claude to do; check the plan it prints
before you confirm. If the plan shows a default interval or agent
mode you did not ask for, do not confirm. Ask again with the values
stated, or run vtriage schedule by hand.

Rules for vclaude_yes:

- Run it right after vclaude, in the same folder. It continues the
  last Claude session in that folder, so another claude call in
  between breaks the link.
- It can run only `vtriage confirm` and `vtriage status`.
- A plan older than 60 minutes cannot be confirmed. Ask again.

## 3. Recorded run on Perlmutter

### The request

```
vclaude "run all jobs in this folder once, check every 10 minutes, 2 jobs per cycle, queue limit 20"
```

```
Here's the plan for `/scratch/user/vt_sched2`:

- 10 folders, all not submitted, 0 currently in queue
- Checks every 10 minutes, submits up to 2 new jobs per cycle, queue limit 20
- Runs for every folder (no path filter)
- Emails you@example.com when done

Nothing has been installed yet. Run `vclaude_yes` to install it — the first cycle will run immediately on confirm.

Cost: 0.0403 USD
```

The plan is saved in `schedule_plan.json` in the folder. The
scrontab table is not touched.

### The plan, as vtriage schedule prints it

Same command run by hand on the first test tree, with a 5 minute
interval:

```
vtriage schedule --every 5m --batch 2 --queue-limit 20
```

```
Schedule plan for /scratch/user/vt_sched
  folders: 10, not submitted: 10, in queue: 0
  every 5m: */5 * * * * (times are UTC)
  new jobs per cycle: 2, queue limit: 20
  path patterns: none, every folder
  email when done: you@example.com

Block to add to the scrontab table:
  # vtriage schedule for /scratch/user/vt_sched
  #SCRON -q cron
  #SCRON -A YOUR_ACCOUNT
  #SCRON -t 00:10:00
  #SCRON -J vtriage_auto
  #SCRON -o /scratch/user/vt_sched/auto_cron.log
  #SCRON --open-mode=append
  */5 * * * * /global/homes/u/user/vasp_triage/vtriage auto --root /scratch/user/vt_sched --batch 2 --queue-limit 20

Nothing installed yet. Plan saved to /scratch/user/vt_sched/schedule_plan.json
On confirm, the block is installed and one cycle runs at once.
To confirm, run:
  vtriage confirm --root /scratch/user/vt_sched
```

### The confirm

vclaude_yes runs this command. Here it was run by hand:

```
vtriage confirm
```

```
Installed in the scrontab table:
  # vtriage schedule for /scratch/user/vt_sched
  #SCRON -q cron
  #SCRON -A YOUR_ACCOUNT
  #SCRON -t 00:10:00
  #SCRON -J vtriage_auto
  #SCRON -o /scratch/user/vt_sched/auto_cron.log
  #SCRON --open-mode=append
  */5 * * * * /global/homes/u/user/vasp_triage/vtriage auto --root /scratch/user/vt_sched --batch 2 --queue-limit 20
Old table saved in /scratch/user/vt_sched/scrontab_backup_20261012_150532.txt

Running the first cycle now.
2026-10-12 15:05 folders: 10, not submitted: 10, in queue: 0

Folders to submit: 2
  /scratch/user/vt_sched/C11/1
  /scratch/user/vt_sched/C11/2
Not submitted now because of the limits: 8
Confirmed by --yes.
Submitted job 59713644: /scratch/user/vt_sched/C11/1
Submitted job 59713652: /scratch/user/vt_sched/C11/2

Submitted: 2
Run the same command again later for the next batch.

Check with: scrontab -l and squeue -u $USER
Watch with: tail -f /scratch/user/vt_sched/auto_cron.log
The entry removes itself after the email is sent.
```

The line Run the same command again later comes from the submit step
and can be ignored here; scrontab runs the next cycles.

### The finish

About 25 minutes later the last cycle wrote AUTO_DONE, sent the
email, and removed its own entry. End of AUTO_DONE:

```
  ionic not converged | /scratch/user/vt_sched/C12/1
  ionic not converged | /scratch/user/vt_sched/C12/2

Email: Submitted batch job 59714115, to you@example.com
Schedule: entry removed from scrontab. Old table saved in /scratch/user/vt_sched/scrontab_backup_20261012_153045.txt
```

The table is back to the welcome comments only:

```
scrontab -l | tail -3
```

```
#

# min hour day-of-month month day-of-week command
```

The two C12 folders end as ionic not converged because they run one
ionic step on purpose. See 04_edit_inputs.md.

## 4. Without Claude

The same three commands work on their own:

```
vtriage schedule --every 20m --batch 10 --path "C11/*" --agent auto
vtriage confirm
vtriage unschedule
```

| Command | Does |
|---|---|
| `vtriage schedule` | shows the block and saves `schedule_plan.json`; installs nothing |
| `vtriage confirm` | installs the saved plan, then runs one cycle at once |
| `vtriage unschedule` | removes the entry for this folder; jobs already submitted keep running |

All three take `--root FOLDER`; without it the current folder is used.

## 5. Intervals

`--every` takes a whole number followed by m or h. Times are UTC.

| You say | --every | Cron line |
|---|---|---|
| every 5 minutes | 5m | `*/5 * * * *` |
| every 10 minutes | 10m | `*/10 * * * *` |
| every 20 minutes | 20m | `*/20 * * * *` |
| every hour | 1h | `7 * * * *` |
| every 2 hours | 2h | `7 */2 * * *` |
| every 5 hours (default) | 5h | `7 */5 * * *` |
| once a day | 24h | `7 0 * * *` |

Minutes go from 5 to 60 and hours from 1 to 24. Intervals given in
hours run at minute 7, away from the busy hour mark. A value that
does not divide 60 or 24, such as 5h, is accepted; the gap across
the hour or across midnight is then shorter, and the plan says so.
Each cycle scans every folder, so keep long campaigns at an hour or
more.

## 6. Safety

- `vtriage schedule` never changes the table. Only `vtriage confirm`
  does, and only from a saved plan less than 60 minutes old.
- The table is read with `scrontab -l` and written back whole, so
  your other entries are kept. A copy of the old table is saved in
  the folder before every change, as `scrontab_backup_DATE.txt`.
- If `scrontab -l` fails, nothing is written.
- A second plan for a folder that already has an entry is refused,
  including an entry you wrote by hand.
- A folder with AUTO_DONE is refused. Delete AUTO_DONE to run the
  campaign again.
- A root or path pattern with % or a space is refused, because cron
  treats % as a line break.
- vclaude can only make plans. Only vclaude_yes can confirm, and
  neither can run unschedule, edit, submit, or auto.
- The decision agent mode is set per campaign with --agent off, ask,
  or auto. Without --agent, AGENT_MODE in local_settings.py is used;
  keep it off. With the agent off, the auto agent submits only not
  submitted folders, and crashed and unconverged folders are listed
  in AUTO_DONE. See 09_decision_agent.md.

## 7. Files written in the folder

| File | Written by | Holds |
|---|---|---|
| schedule_plan.json | schedule | the block and options; deleted on confirm |
| scrontab_backup_DATE.txt | confirm, unschedule, the finish | the table before each change |
| auto_cron.log | every scheduled cycle | one summary line per cycle |
| AUTO_DONE | the finish | counts, folders that need a look, email and removal lines |
| agent_state.json, agent_plan.json, agent_summary.txt | the decision agent, when the agent is ask or auto | see 09_decision_agent.md |

## 8. Problems

| Message | Fix |
|---|---|
| Error: the plan is older than 60 minutes | run vtriage schedule again |
| Error: the scrontab table already has an entry | run vtriage unschedule, or wait for the campaign to finish |
| Error: AUTO_DONE exists | the campaign is finished; delete AUTO_DONE to rerun |
| Error: no account | set SCHEDULE_ACCOUNT in local_settings.py |
| Error: scrontab -l failed | NERSC Slurm problem or scrontab disabled; nothing was written |
| Schedule: not removed | the finish could not edit the table; run vtriage unschedule |
| vclaude_yes says there is no plan | run it in the same folder right after vclaude |
| Entries look commented out | NERSC disables entries before maintenance; unschedule still finds and removes them |