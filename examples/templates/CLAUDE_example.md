# vasp_triage instructions

For job status, run vtriage status in the target folder.
Do not read OUTCAR, OSZICAR, or slurm files yourself for status.
For details on a folder, run vtriage report and read report.md.
Keep summaries short: counts by status, then the Needs a look list.

Never run vtriage edit, submit, history, or auto yourself.
Never run scrontab yourself.
Print the exact command for the user to run instead.

Command syntax:
Submit and edit need exactly one of --status, --group, or --list.
Folders are chosen with --path, never as plain arguments.
Patterns: C11/2, C11/*, C11/{2..10}, C11/{2,5}. Quote each one.
Statuses: "not submitted", crashed, incomplete, "SCF not converged",
"ionic not converged", converged, "crashed after reaching accuracy".
Groups: converged, almost_converged, not_converged, failed, other.

Examples:
vtriage submit --status "not submitted" --path "C11/{2..4}" "C12/*"
vtriage submit --group failed --max 10
vtriage edit --status "not submitted" --path "C12/*" --set NELM=120
vtriage edit --group not_converged --set ALGO=Normal --set NELM=200

Running automatically:
When the user asks to run automatically, to use the auto agent, or
to set up scrontab, print these numbered steps with the real folder
path filled in. Use the batch, queue limit, interval, and path
patterns the user asked for; otherwise leave out --batch and
--queue-limit so local_settings.py decides, and use every 5 hours.
The auto agent submits only not submitted folders and stops by
itself when the campaign is done.

1. Check AUTO_EMAIL and AUTO_EMAIL_SBATCH_OPTIONS in
   ~/vasp_triage/local_settings.py.
2. Run one cycle by hand and read the output:
   vtriage auto --root FOLDER
3. Run scrontab -e, go to the end (G, then o in vi), paste the
   block below, press Esc, type :wq.
4. Check it with scrontab -l and squeue -u $USER. The vtriage_auto
   job pending with BeginTime is normal.
5. Watch it with tail -f FOLDER/auto_cron.log.
6. When AUTO_DONE appears and the email arrives, run scrontab -e
   and delete the seven lines.

Block for step 3 (times are UTC; ACCOUNT is the user's NERSC
project, ask if unknown):
#SCRON -q cron
#SCRON -A ACCOUNT
#SCRON -t 00:10:00
#SCRON -J vtriage_auto
#SCRON -o FOLDER/auto_cron.log
#SCRON --open-mode=append
7 */5 * * * $HOME/vasp_triage/vtriage auto --root FOLDER

Interval lines: every 5 minutes is */5 * * * *, every hour is
7 * * * *, every 5 hours is 7 */5 * * *. Tell the user to replace
$HOME with the output of echo $HOME, since scrontab does not read
~/.bashrc.
Remind the user that NERSC comments out entries before maintenance,
and that auto never resubmits crashed or unconverged folders.