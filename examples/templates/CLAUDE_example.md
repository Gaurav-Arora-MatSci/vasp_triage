# vasp_triage instructions

For job status, run vtriage status in the target folder.
Do not read OUTCAR, OSZICAR, or slurm files yourself for status.
For details on a folder, run vtriage report and read report.md.
Keep summaries short: counts by status, then the Needs a look list.

Never run vtriage edit, submit, history, auto, or unschedule
yourself. Never run scrontab yourself.
Run vtriage confirm only when the user's latest message is a yes to
a schedule plan you showed in your previous answer.
Print the exact command for the user to run instead.

Command syntax:
Submit and edit need exactly one of --status, --group, or --list.
Folders are chosen with --path, never as plain arguments.
Patterns: C11/2, C11/*, C11/{2..10}, C11/{2,5}. Quote each one.
Without --path, every folder under the current folder is used. Never
write --path . or --path with the folder you are in.
Statuses: "not submitted", crashed, incomplete, "SCF not converged",
"ionic not converged", converged, "crashed after reaching accuracy".
Groups: converged, almost_converged, not_converged, failed, other.

Examples:
vtriage submit --status "not submitted" --path "C11/{2..4}" "C12/*"
vtriage submit --group failed --max 10
vtriage edit --status "not submitted" --path "C12/*" --set NELM=120
vtriage edit --group not_converged --set ALGO=Normal --set NELM=200

Running automatically (NERSC Perlmutter only):
When the user asks to submit or run the not submitted jobs, to run
all jobs in a folder, to run automatically, or to check on an
interval, run vtriage schedule in that folder. It only shows a plan
and installs nothing. Then show the plan and tell the user to run
vclaude_yes to install it. Without an interval in the request, leave
out --every, so the default applies.
A request to submit folders with any other status, such as crashed
or not converged, is not a schedule request. Print the vtriage
submit command for the user instead.

vtriage schedule options:
--every: time between checks, a whole number then m or h, such as
20m or 5h. Minutes from 5 to 60, hours from 1 to 24. Default 5h.
--batch N and --queue-limit N: only when the user gives them;
otherwise local_settings.py decides.
--path: patterns, as for submit and edit.

Turn the user's words into --every: every 20 minutes is 20m, every
2 hours is 2h, hourly is 1h, daily is 24h. If the interval cannot be
written this way, such as every 90 minutes, run nothing, say so, and
offer the nearest valid values, such as 1h or 2h.

Example:
vtriage schedule --every 20m --batch 10 --path "C11/*"

On confirm, the entry is installed and one cycle runs at once. The
auto agent submits only not submitted folders, never resubmits
crashed or unconverged folders, sends the email when done, and
removes its own scrontab entry. To stop it early, the user runs
vtriage unschedule in that folder.
If schedule fails because scrontab is missing or disabled, say that
scheduling works only on Perlmutter, and give the hand command
vtriage auto --root FOLDER instead.
