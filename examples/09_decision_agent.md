# 9. The decision agent: continue unconverged runs, with limits

The auto agent in guide 05 submits new folders and stops there.
Crashed and unconverged folders wait for you. The decision agent
adds one step to each auto cycle. It looks at the folders that
finished without converging and continues the ones that are safe to
continue. Everything else still waits for you.

It is off by default. Turn it on for one campaign with --agent ask or
--agent auto. It needs Claude Code on the login node, so it is
written for NERSC Perlmutter, where both the API and scrontab work.

## 1. What it does

| Case | Who decides | Action |
|---|---|---|
| ionic not converged | Claude judges the trend | still improving: CONTCAR to POSCAR, resubmit; otherwise wait |
| walltime hit in a relaxation | rule | CONTCAR to POSCAR, resubmit |
| walltime hit in a static run | rule | wait |
| SCF not converged | Claude judges the trend | dE still falling: raise NELM, rerun; otherwise wait |
| crashed after reaching accuracy | rule | done, listed |
| CONTCAR empty, missing, or cut short | rule | skipped, listed |
| MD or finite difference run, IBRION not 1, 2, or 3 | rule | wait, noted as not a relaxation |
| no slurm file in the folder | rule | wait, noted as no slurm file to read |
| any other crash, incomplete | rule | wait |

Limits, checked by the code before anything is written:

- At most 3 runs per relaxation, counting the first: 2 CONTCAR
  restarts (AGENT_MAX_IONIC_RESTARTS = 2). After the third run, the
  folder is listed as not converged after 3 runs, and waits for you.
- At most 2 runs per SCF case, counting the first: 1 NELM rerun
  (AGENT_MAX_SCF_RERUNS = 1).
- NELM never above 150 (AGENT_MAX_NELM). A larger value from Claude
  is cut to 150. A value not larger than the current NELM means wait.
- After an agent restart, the final energy may rise by at most
  1 meV per atom over the run before (AGENT_ENERGY_RISE_PER_ATOM). A
  restarted cell relaxation can end slightly higher, because the
  plane wave basis is set up again. A larger rise stops the folder.
- A walltime restart waits for you if the last electronic loop was
  at NELM, since more time would not fix that.
- The runs are counted by job ID. The agent keeps the ID of each job
  it submits. When you resubmit a folder yourself, the next run has
  an ID the agent did not submit, so the count starts again.
- Each restart and rerun is also written to progress.txt as a line
  that starts with Agent:, with the reason.
- If sbatch refuses a job, for example at the debug limit of 5
  submitted jobs, the agent puts INCAR and POSCAR back as they were.
  The next cycle submits again with no new LLM call. The report says
  why the first submit failed. After 3 refusals
  (AGENT_SUBMIT_TRIES), the folder waits for you.

## 2. Why it cannot leave the folder

- Claude gets no tools. The call removes every built in tool and
  every MCP tool (--tools "" and --disallowedTools "mcp__*"). It can
  only answer in text.
- vasp_triage reads OSZICAR and OUTCAR itself and puts the numbers in
  the prompt: the energy per ionic step, the change per step, the
  largest force per step, and the electronic steps per ionic step.
  For SCF cases, the dE and d eps of the last electronic loop, each
  step marked fixed density or density updated, and any change of
  method such as DAV to RMM. The steps before the first rms(c) value
  in OSZICAR are the fixed density steps.
- Claude answers restart, rerun, or wait, with a one sentence reason.
  Any other answer becomes wait.
- Only the code writes files: the archive copies, POSCAR, INCAR,
  progress.txt, and three agent files in the root. Before each write
  it checks that the folder is inside the root, after following
  links, and that its job is not in the queue.
- Each folder is archived as NAME-N before it is changed.
- The call replaces Claude Code's system prompt, runs one turn, and
  is not saved as a session (--no-session-persistence).

Two things still happen outside the folder, both done by vasp_triage,
not by Claude: the activity log push to your private log repository,
and the Slurm mail job. Claude Code itself reads its own settings in
~/.claude when it starts.

## 3. Cost

| Limit | Default | When it is reached |
|---|---|---|
| AGENT_COST_PER_PASS | 0.50 USD | the call stops (--max-budget-usd) |
| AGENT_COST_CAMPAIGN | 1.50 USD | no more calls; folders that need judgment wait for you |

The per call limit is a ceiling, not the price. In tests a call cost
about 0.002 USD plus 0.007 USD per folder, so about 0.07 USD for 10
folders. An earlier limit of 0.05 USD was too low for 10 folders: the
call stopped and its answer was lost.

Claude is called only in a cycle that has new ionic or SCF cases,
and once for all of them, at most AGENT_MAX_FOLDERS_PER_CALL (10)
folders per call. The rest wait for the next cycle. Rule cases cost
nothing. The recorded calls below cost 0.0281 and 0.0102 USD for 4
and 1 folders. The total is kept in agent_state.json.

## 4. Setup on Perlmutter

Step 1. Check that claude works in a job with a clean environment,
like a scrontab job. Run on a login node:

```
sbatch -A YOUR_ACCOUNT -q debug -C cpu -N 1 -t 2 --export=NONE -o claude_test.out --wrap='echo HOME=$HOME; /global/homes/u/user/.local/bin/claude -p "Reply with OK" --model sonnet'
```

When the job ends, cat claude_test.out must show the HOME line and
OK. Find your claude path with which claude.

Step 2. Add these lines to local_settings.py in the vasp_triage
folder:

```python
AGENT_MODE = "off"
AGENT_CLAUDE_COMMAND = "/global/homes/u/user/.local/bin/claude"
```

AGENT_MODE is the mode for every campaign started without --agent,
including campaigns already on the schedule. Keep it off and choose
the mode per campaign. The other AGENT_ settings have the defaults in
section 1. Set them here only to change them.

Step 3. Try it on a copied tree first, by hand, with one cycle:

```
cd /scratch/user/vt_agent
vtriage auto --agent ask
```

Step 4. Start the schedule as in guide 08, with the mode for this
campaign:

```
vtriage schedule --every 2h --agent ask
vtriage confirm
```

The plan shows the line decision agent: ask, and the cron line ends
with --agent ask. Start with ask. Switch to auto once the plans look
right: vtriage unschedule, then schedule again with --agent auto.

## 5. Ask mode, recorded

In ask mode the agent writes agent_plan.json and submits nothing for
those folders. New folders are still submitted as usual.

```
$ vtriage auto --agent ask
2026-10-14 14:12 folders: 12, not submitted: 1, in queue: 0
vtriage agent, 2026-10-14 14:12
Root: /scratch/user/vt_agent
Mode: ask. LLM cost this cycle: 0.0281 USD. Campaign total: 0.0281 of 1.50 USD.

Planned, waiting for vtriage approve (3):
  wall_relax: restart from CONTCAR. rule: walltime hit, no VASP error
  ionic_good: restart from CONTCAR. LLM: Energy drops steadily by 0.01 eV per step with no oscillation, and max force falls from 0.50 to 0.067 eV/A, approaching the 0.01 limit.
  scf_good: raise NELM to 100 and rerun. LLM: dE falls steadily by about 15% per step to 6.85e-06 at step 60, so about 12 more steps reach 1e-06; NELM 100 gives margin.

Waiting for you (5):
  incomplete: stopped without a known error, possibly a node failure
  oom: crashed: out of memory
  wall_static: walltime hit on a static run
  ionic_osc: LLM: Energy oscillates between -19.998 and -20.002 eV every step and max force alternates 0.25/0.15 eV/A, far above the 0.01 limit, so there is no real progress.
  scf_bad: LLM: dE falls only about 5% per step, from 8.15e-03 to 4.85e-03, so reaching 1e-06 needs roughly 170 more steps, which exceeds the 150 maximum NELM.

Skipped, check CONTCAR (1):
  ionic_nocontcar: CONTCAR missing or empty

Done, reached required accuracy before the job died (1):
  relax_done_crash: reached required accuracy before the job died, treated as done

Run vtriage approve --root /scratch/user/vt_agent to see and apply the plan.

Email: Submitted batch job 1001, to you@example.com

Folders to submit: 1
  /scratch/user/vt_agent/fresh
Confirmed by --yes.
Submitted job 1002: /scratch/user/vt_agent/fresh

Submitted: 1
```

The email subject was vtriage_plan_vt_agent_3toapprove_6you: 3
actions to approve, and 6 folders that wait for you or were skipped.

A plan that waits is kept as it is. The next cycle makes no new LLM
call for those folders:

```
$ vtriage auto --agent ask   (next cycle, plan still waiting)
2026-10-14 14:12 folders: 12, not submitted: 0, in queue: 1
All submitted. Waiting for 1 jobs to leave the queue.
```

Approve all, none, or some. Type yes, no, or the numbers, such as
1 3. Folders you leave out are marked rejected by you and wait.

```
$ vtriage approve
Plan made 2026-10-14 14:12 for /scratch/user/vt_agent

1. wall_relax: restart from CONTCAR
   rule: walltime hit, no VASP error
2. ionic_good: restart from CONTCAR
   LLM: Energy drops steadily by 0.01 eV per step with no oscillation, and max force falls from 0.50 to 0.067 eV/A, approaching the 0.01 limit.
3. scf_good: raise NELM to 100 and rerun
   LLM: dE falls steadily by about 15% per step to 6.85e-06 at step 60, so about 12 more steps reach 1e-06; NELM 100 gives margin.

Type yes to apply all, no to reject all, or the numbers to apply, such as 1 3: yes
Archived as run 1: /scratch/user/vt_agent/wall_relax

wall_relax: restarted from CONTCAR, run 2 of 3, job 1003. Approved by you. rule: walltime hit, no VASP error
ionic_good: restarted from CONTCAR, run 2 of 3, job 1004. Approved by you. LLM: Energy drops steadily by 0.01 eV per step with no oscillation, and max force falls from 0.50 to 0.067 eV/A, approaching the 0.01 limit.
scf_good: NELM 60 -> 100, rerun, job 1005. Approved by you. LLM: dE falls steadily by about 15% per step to 6.85e-06 at step 60, so about 12 more steps reach 1e-06; NELM 100 gives margin.
```

vtriage approve checks each folder again first. A folder whose status
or job changed since the plan is skipped. It takes the same lock as
the auto cycle, so the two never act at the same time.

## 6. Auto mode, recorded

After those jobs ended, the next cycle ran with --agent auto:

```
$ vtriage auto --agent auto   (after the jobs ended)
2026-10-14 14:12 folders: 12, not submitted: 0, in queue: 0
vtriage agent, 2026-10-14 14:12
Root: /scratch/user/vt_agent
Mode: auto. LLM cost this cycle: 0.0102 USD. Campaign total: 0.0384 of 1.50 USD.

Restarted from CONTCAR (1):
  ionic_good: restarted from CONTCAR, run 3 of 3, job 1006. LLM: Energy drops steadily by 0.01 eV per step and max force falls from 0.0600 to 0.0081 eV/A, already below the 0.01 EDIFFG limit, with stable 8 electronic steps.

Waiting for you (2):
  scf_good: SCF not converged after 2 runs, the most allowed
  wall_relax: no energy drop since the last restart: -20.050000 eV before, -20.035000 eV now, more than 0.0020 eV higher

Email: Submitted batch job 1007, to you@example.com
Agent work still open. Waiting.
```

scf_good and wall_relax were stopped by rules, with no LLM call.
wall_relax ended 15 meV higher than its first run, above the 2 meV
allowed for its 2 atoms. ionic_good was restarted a second time, its
third and last allowed run. When that run ended still not converged,
the next cycle stopped it by rule and finished the campaign:

```
$ vtriage auto --agent auto   (after run 3 ended)
2026-10-14 14:12 folders: 12, not submitted: 0, in queue: 0
vtriage agent, 2026-10-14 14:12
Root: /scratch/user/vt_agent
Mode: auto. LLM cost this cycle: 0.0000 USD. Campaign total: 0.0384 of 1.50 USD.

Waiting for you (1):
  ionic_good: not converged after 3 runs, the most allowed

Email: Submitted batch job 1008, to you@example.com
Nothing left to submit and nothing in the queue.
```

The lines written to progress.txt:

```
$ grep Agent ionic_good/progress.txt
  Agent: restart from CONTCAR, run 2 of 3. Energy drops steadily by 0.01 eV per step with no oscillation, and max force falls from 0.50 to 0.067 eV/A, approaching the 0.01 limit.
  Agent: restart from CONTCAR, run 3 of 3. Energy drops steadily by 0.01 eV per step and max force falls from 0.0600 to 0.0081 eV/A, already below the 0.01 EDIFFG limit, with stable 8 electronic steps.
```

Each line of AUTO_DONE ends with the agent's note, and a line gives
the LLM cost:

```
Folders that need a look: 10
  incomplete | /scratch/user/vt_agent/incomplete | agent: wait, stopped without a known error, possibly a node failure
  ionic not converged | /scratch/user/vt_agent/ionic_good | agent: wait, not converged after 3 runs, the most allowed
  ionic not converged | /scratch/user/vt_agent/ionic_nocontcar | agent: skip, CONTCAR missing or empty
  ionic not converged | /scratch/user/vt_agent/ionic_osc | agent: wait, LLM: Energy oscillates between -19.998 and -20.002 eV every step and max force alternates 0.25/0.15 eV/A, far above the 0.01 limit, so there is no real progress.
  crashed | /scratch/user/vt_agent/oom | out of memory | agent: wait, crashed: out of memory
  crashed after reaching accuracy | /scratch/user/vt_agent/relax_done_crash | agent: done, reached required accuracy before the job died, treated as done
  SCF not converged | /scratch/user/vt_agent/scf_bad | last SCF hit NELM | agent: wait, LLM: dE falls only about 5% per step, from 8.15e-03 to 4.85e-03, so reaching 1e-06 needs roughly 170 more steps, which exceeds the 150 maximum NELM.
  SCF not converged | /scratch/user/vt_agent/scf_good | last SCF hit NELM | agent: wait, SCF not converged after 2 runs, the most allowed
  crashed | /scratch/user/vt_agent/wall_relax | walltime | agent: wait, no energy drop since the last restart: -20.050000 eV before, -20.035000 eV now, more than 0.0020 eV higher
  crashed | /scratch/user/vt_agent/wall_static | walltime | agent: wait, walltime hit on a static run

Agent LLM cost: 0.0384 USD in 2 calls
```

## 7. When a campaign finishes

The campaign finishes when nothing is left to submit, no campaign job
is in the queue, no plan waits for approval, and no folder was put
off to a later cycle. Folders that wait for you do not hold it open.
They are listed in AUTO_DONE with the reason.

To continue after you fix them, use edit and submit as usual, delete
AUTO_DONE, and schedule again. A folder with a new job counts as new
to the agent.

## 8. Files written in the root folder

| File | Holds |
|---|---|
| agent_state.json | the decision for each folder and job, the job IDs it submitted, the money spent |
| agent_plan.json | actions waiting for vtriage approve, ask mode only |
| agent_summary.txt | the plain English summary of the latest cycle |
| vtriage_agent.out | output of the mail job, the same summary |

To let the agent look at every folder again and reset the cost,
delete agent_state.json. A damaged agent_state.json, for example from
a job stopped while writing it, is kept as
agent_state.json.broken_DATE with a warning, and the agent starts
with an empty one. The files are written in one step, so this should
not happen.

## 9. Commands without the schedule

```
vtriage auto --agent ask  # one cycle, agent plans only
vtriage approve           # show and apply the plan, ask mode
python3 ~/vasp_triage/evidence.py FOLDER    # the numbers Claude sees
```

## 10. Where this output came from

A local run on 14 October 2026. The folders hold synthetic VASP
output made for each case. The answers are real answers from Claude
Code 2.1.296 with the sonnet model, called exactly as on the cluster.
sbatch and squeue were stand in scripts, so the job IDs are not real.

## 11. Problems

| Problem | Cause and fix |
|---|---|
| LLM call failed: claude not found | set AGENT_CLAUDE_COMMAND to the full path from which claude |
| LLM call failed, every cycle | read auto_cron.log; the folders are tried again each cycle until AGENT_COST_CAMPAIGN |
| Warning: agent mode ... stays off | AGENT_MODE must be off, ask, or auto |
| the agent acted in another campaign | AGENT_MODE in local_settings.py is not off; set it to off and use --agent |
| An auto cycle is running now | vtriage approve waits for the lock; try again in a minute |
| N folder(s) put off to the next cycle | queue limit full or more than 10 folders for Claude; they are handled later |
| campaign LLM cost limit reached | raise AGENT_COST_CAMPAIGN, or decide those folders yourself |
| refused by sbatch, Try 1 of 3 | sbatch did not accept the job, for example QOSMaxSubmitJobPerUserLimit; it is tried again next cycle |
| sbatch refused it 3 times | the files are as before; check the error, then submit by hand |
| no slurm file to read | the job script does not write slurm-JOBID.out; use #SBATCH -o slurm-%j.out |
| not a relaxation | IBRION is not 1, 2, or 3; MD and finite difference runs are never restarted |
