# vasp_triage examples

Worked examples for every vasp_triage command, with the real output
each one printed. Read them in order the first time. Later, jump to
the file you need.

| File | What it covers |
|---|---|
| [01_setup.md](01_setup.md) | clone, PATH, local_settings.py, first check |
| [02_status_and_report.md](02_status_and_report.md) | status, list folders, report, history |
| [03_select_folders_by_path.md](03_select_folders_by_path.md) | choose exact folders with path patterns, command line and menu |
| [04_edit_inputs.md](04_edit_inputs.md) | change INCAR and KPOINTS in chosen folders |
| [05_auto_agent_scrontab.md](05_auto_agent_scrontab.md) | let vasp_triage submit a whole campaign on a schedule and email you at the end |
| [06_llm_vclaude.md](06_llm_vclaude.md) | ask in plain English through Claude Code |
| [07_troubleshooting.md](07_troubleshooting.md) | every problem met so far and its fix |

Ready to copy files are in [templates](templates):

| Template | Use |
|---|---|
| local_settings_example.py | per machine settings, copy to the repo folder as local_settings.py |
| submit_vasp_test.sh | short job script for test runs |
| make_test_tree.sh | builds the 10 folder test tree used in these examples |
| scrontab_example.txt | scheduled auto agent entries for NERSC |
| CLAUDE_example.md | instructions file for Claude Code |
| vclaude.sh | the plain English wrapper |

## Where the output comes from

Two sources, both real runs of the code:

1. NERSC Perlmutter, 11 October 2026: the LLM answers and costs, the
   scrontab screens, the email subject, and the auto agent finish.
2. A local run of the same code with stand in sbatch and squeue
   scripts, on the same 10 folder layout: everything else. The
   behaviour of vasp_triage is the same; only the job IDs and the
   job states come from the stand in tools.

Personal details are replaced: user for the user name, YOUR_ACCOUNT
for the NERSC project, you@example.com for the email address, and
/scratch/user/vt_test for the test folder.

## The test tree

Every example uses this layout:

```
vt_test
├── C11
│   ├── 1
│   ├── 2
│   ├── 3
│   ├── 4
│   ├── 5
│   └── 6
├── C12
│   ├── 1
│   └── 2
└── C44
    ├── x
    └── y
```

Each folder holds INCAR, KPOINTS, POSCAR, POTCAR, and submit_vasp.sh
for a 2 atom bcc W cell with a 1x1x1 Gamma mesh. C12 folders run one
ionic step, so they end as ionic not converged. The rest are static
runs that converge. Build it with templates/make_test_tree.sh.

## Version

Path patterns, submit --yes, and the auto agent need the version
that contains auto.py. The other examples also work with v1.0.0.
Check with:

```
vtriage menu
```

The banner prints the version.
