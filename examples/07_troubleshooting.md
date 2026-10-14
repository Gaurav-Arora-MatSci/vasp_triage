# 7. Troubleshooting

Every problem met while building and testing vasp_triage, with the
fix.

## Setup

**which vtriage prints nothing.**
The repo folder is not on PATH. Add
export PATH=$HOME/vasp_triage:$PATH to ~/.bashrc and run
source ~/.bashrc.

**A new option is missing, for example no path pattern step in the
menu.**
An old copy is running. Check which one:

```
which vtriage
grep -n "path pattern" ~/vasp_triage/menu.py
```

If grep prints nothing, copy the new files into the folder that
which vtriage points to.

**git pull overwrote my limits.**
Per machine values belong in local_settings.py, which git ignores,
not in config.py.

## Status

**The folder count does not match find . -name INCAR | wc -l.**
A folder holds several runs, or a parent folder has a shared INCAR.
vasp_triage expects one calculation per folder.

**A folder shows missing inputs.**
One of INCAR, KPOINTS, POSCAR, POTCAR, submit_vasp.sh is missing.
vtriage menu, then 2, then the missing inputs status lists which.

**A folder shows incomplete.**
The job died with a message vasp_triage does not know yet. Look at
the end of its slurm file. Error patterns come from custodian, so
send the message as an issue to add it.

**Needs a look says SCF at NELM, but OUTCAR says reached required
accuracy.**
The ionic criterion was met with an unconverged last electronic
loop. That is not convergence, and the label is correct. If the
slurm file also shows oom_kill, the job was killed too; the label
shows only the SCF part.

## Submit

**Error: give exactly one of --status, --group, or --list.**
Folders cannot be given as plain arguments. Use
--status "not submitted" --path "C11/2".

**No selected folder matches: C11/1.**
Either a typo, or the folder has a different status than the one
chosen. A folder just submitted is running or pending, not not
submitted.

**Path filter kept 0 of 10 folders with --path C11.**
C11 is a parent, not a calculation. Use C11/*.

**The shell changed my pattern.**
Quote each pattern on the command line: --path "C11/*".

**CONTCAR missing or empty, skipped.**
A relaxation restart needs CONTCAR. The folder is skipped rather
than restarted from the wrong structure.

**Running, skipped.**
The folder is in the queue. It is never submitted twice.

**Jobs stay pending with a QOS limit reason.**
The debug queue limits how many jobs one user can have. Lower
--queue-limit.

## Job script and INCAR for tests

**The test job is rejected or held.**
The debug queue on Perlmutter allows a short wall time, 30 minutes
as far as known. -t 5:00:00 is too long. Use -t 00:10:00.

**VASP crashes on the 2 atom test cell.**
128 MPI ranks on 2 atoms make VASP raise NBANDS. Use srun -n 8.
Remove KPAR and NCORE that need more ranks or more k points.

## Auto agent

**Error: no calculation folders match. Check --root and --path.**
Wrong --root, a typo in --path, or the INCAR files are gone. Check
with find . -name INCAR | wc -l. The agent does not write AUTO_DONE
in this case, on purpose.

**Queue full every cycle.**
The queue limit counts all your jobs from every project. Raise
--queue-limit, or wait.

**The vtriage_auto job is always in squeue, pending with
BeginTime.**
Normal. scrontab keeps it queued until the next start time.

**A second campaign's job stays pending with reason Dependency, and
its auto_cron.log never appears.**
NERSC gives scrontab jobs a singleton dependency: a job waits until
every earlier job with the same name and user has ended. Two
scrontab entries named vtriage_auto block each other, and one never
runs. scontrol show job N shows Dependency=singleton(unfulfilled).
Since v1.3.0, vtriage schedule names each entry
vtriage_auto_FOLDER_HASH. For an older entry, run vtriage unschedule
and vtriage schedule again, or change its -J line by hand with
scrontab -e.

**sbatch: error: QOSMaxSubmitJobPerUserLimit in the debug queue.**
On Perlmutter CPU, debug allows 5 submitted jobs per user. The
refused folders stay not submitted and go in the next cycle. Use
--batch 5 or less for debug test trees.

**Two cycles might submit the same folders.**
They cannot. A lock file lets one cycle run at a time. Another auto
run is active. Skipped. means the lock worked.

**AUTO_DONE was written but I added more folders.**
Delete AUTO_DONE. The next cycle continues.

**The scheduled job still runs after AUTO_DONE.**
Expected. Each run exits at once. Remove the entry with scrontab -e.

**The scrontab entry disappeared or is commented out.**
NERSC comments out entries it cancels, for example before
maintenance. Remove the comment marks with scrontab -e.

**No email.**
Test Slurm mail with a tiny job, see 05_auto_agent_scrontab.md.
mail and mailx do not work on Perlmutter because sendmail is
missing; delete ~/dead.letter. Check AUTO_EMAIL and
AUTO_EMAIL_SBATCH_OPTIONS in local_settings.py, and look in spam.

**The email says CANCELLED with zero run time.**
The email job was cancelled by hand. The counts in the subject are
still right.

## LLM

**Claude suggests commands like vtriage submit C11/2.**
~/.claude/CLAUDE.md lacks the syntax block, or is not loaded. Copy
templates/CLAUDE_example.md and check with /memory.

**claude.md is ignored.**
The name must be CLAUDE.md in capitals.

**A status check takes minutes and costs much more than 0.05 USD.**
--allowedTools is missing, so Claude reads files itself. Use vclaude
or add --allowedTools "Bash(vtriage status)".

**KeyError: result after Ctrl+C.**
The run was stopped before Claude answered. The vclaude template
prints a short message instead.

**Claude will not set up scrontab.**
By design. It prints the steps and the block; you paste it with
scrontab -e. If it gives no steps, ~/.claude/CLAUDE.md lacks the
Running automatically section; copy templates/CLAUDE_example.md
again.

**curl to api.anthropic.com resets.**
The cluster blocks the API. Use vtriage without the LLM there.
