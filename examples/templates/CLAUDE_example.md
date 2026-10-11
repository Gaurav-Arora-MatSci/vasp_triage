# vasp_triage instructions

For job status, run vtriage status in the target folder.
Do not read OUTCAR, OSZICAR, or slurm files yourself for status.
For details on a folder, run vtriage report and read report.md.
Keep summaries short: counts by status, then the Needs a look list.

Never run vtriage edit, submit, history, or auto yourself.
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
