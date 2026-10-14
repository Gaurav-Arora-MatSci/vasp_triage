# 6. Plain English through Claude Code

With AGENT_MODE off, the default, vasp_triage has no LLM inside it
and makes no network calls. You can
put one on top: Claude Code runs on the login node, reads your
request, runs vtriage status or vtriage report, and answers. For
anything that changes files or submits jobs, it prints the exact
vtriage command for you to run and confirm.

Everything in this file is optional. vasp_triage works the same
without it.

## 1. Check that the cluster can reach the API

On the login node:

```
curl -sS -o /dev/null -w "%{http_code}\n" https://api.anthropic.com
```

A number such as 404 or 405 means reachable. A connection reset or a
timeout means the cluster blocks it, and this file does not apply
there.

| Cluster | Result |
|---|---|
| NERSC Perlmutter | reachable, verified working |
| TACC Stampede3 | reachable, 405 |
| Villanova Augie | blocked, connection reset |

## 2. Install and log in

Install Claude Code following https://code.claude.com/docs/en/setup.
Then:

```
claude
```

The first start asks you to log in. Inside Claude Code:

```
/status
```

shows how you are logged in. Claude Code takes credentials from one
of two places:

1. The ANTHROPIC_API_KEY environment variable. In -p mode it is
   always used when set.
2. A saved login in ~/.claude/.credentials.json, written by /login.

Check without printing the whole key:

```
echo ${ANTHROPIC_API_KEY:0:12}
ls -l ~/.claude/.credentials.json
grep -n ANTHROPIC_API_KEY ~/.bashrc
```

On a shared cluster the credentials file must show -rw-------. If
not:

```
chmod 600 ~/.claude/.credentials.json
```

Never commit the key or that file to git. /logout removes a stored
login. Usage and billing are on the Console at platform.claude.com.

## 3. Tell Claude how vtriage works

Claude Code reads ~/.claude/CLAUDE.md at every start. Copy the
template:

```
mkdir -p ~/.claude
cp ~/vasp_triage/examples/templates/CLAUDE_example.md ~/.claude/CLAUDE.md
```

The name must be CLAUDE.md in capitals. Linux is case sensitive, and
claude.md is not loaded. Do not put it inside the vasp_triage folder.

Check that it is loaded:

```
cd /scratch/user/vt_test
claude
/memory
/exit
```

/memory lists ~/.claude/CLAUDE.md.

The syntax block in that file matters. Without it, Claude guessed
the command format. These were real answers before the block was
added:

```
$ vclaude "submit only C11 folders 2 to 4 that were not submitted"

All 10 folders currently show as "not submitted," which includes C11/2, C11/3, and C11/4.

Run this to submit them:

    vtriage submit C11/2 C11/3 C11/4

Cost: 0.0369 USD

$ vclaude "set NELM to 120 in C12 folders"
There are two job folders under C12: `C12/1` and `C12/2`. Per instructions, I won't run `vtriage edit` myself — here are the commands to run:

    vtriage edit C12/1 --set NELM=120
    vtriage edit C12/2 --set NELM=120

Cost: 0.0396 USD
```

Both commands are invalid: folders go in --path, and a status or
group is required. They fail with an error, so nothing harmful
happens, but they are wrong. With the block in place, see section 6.

## 4. Add the vclaude wrapper

```
cat ~/vasp_triage/examples/templates/vclaude.sh >> ~/.bashrc
source ~/.bashrc
```

vclaude "request" runs Claude once, lets it run only vtriage status
and vtriage report, and prints the answer and the cost.

## 5. One line commands without the wrapper

Ask once, with permission for one command only:

```
cd /scratch/user/vt_test
claude -p "Run vtriage status here and summarize it" \
  --model sonnet --allowedTools "Bash(vtriage status)"
```

Without --allowedTools, the Bash call to vtriage is refused, because
-p cannot ask for permission. Claude then reads OUTCAR files itself,
which is slow and costly.

Get the cost as well:

```
claude -p "check the status of this folder by running vtriage status" \
  --model sonnet --allowedTools "Bash(vtriage status)" \
  --output-format json > run.json
python3 -c "import json; d=json.load(open('run.json')); print(d['result']); print(d['total_cost_usd'])"
```

Cap the spend of one run with --max-budget-usd 0.10.

## 6. Real answers on the test tree, Perlmutter

Status:

```
$ vclaude "check the status of this folder"

No jobs from this folder yet — all 10 subfolders under it are **not submitted**. (Separately, you have 2 jobs queued elsewhere: 1 pending, 1 running, 13 free slots.)

Needs a look: nothing to review yet since nothing's been submitted here. Let me know if you'd like to submit them (I won't run `vtriage submit` myself — just say the word and I'll give you the exact command).

Cost: 0.0345 USD
```

A submit request. It prints the command and does not run it:

```
$ vclaude "submit only C11 folders 2 to 4 that were not submitted"
Run this command:

    vtriage submit --status "not submitted" --path "C11/{2..4}"

Cost: 0.0150 USD
```

An edit request:

```
$ vclaude "set NELM to 120 in C12 folders"
Run this command yourself:

    vtriage edit --status "not submitted" --path "C12/*" --set NELM=120

Cost: 0.0151 USD
```

Run each printed command yourself. vtriage then shows the preview
and waits for your yes, as always.

A request to resubmit crashed jobs. It runs nothing:

```
$ vclaude "resubmit all crashed jobs now"

No crashed jobs found — all 10 folders here show as "not submitted," and none of the jobs currently in the queue are from this folder. There's nothing to resubmit.

If you want to double check a specific folder's details, run:

    vtriage report

Cost: 0.0254 USD
```

A request naming a folder that does not exist. It asks instead of
guessing:

```
$ vclaude "submit the not submitted folders 2 to 4 in C11 and 3 to 4 in C22"
I can only search within `/scratch/user/vt_test`, and there's no `C22` folder there — only `C11`, `C12`, and `C44`. Did you mean `C12` (which has subfolders 3 to 4 — but C12 only has subfolders 1 and 2, so 3-4 don't exist there either)? Could you confirm the correct folder names?

Cost: 0.0602 USD
```

## Running automatically through Claude

Claude does not install scrontab entries. scrontab -e opens an
editor that Claude cannot use, and the other way, scrontab FILE,
replaces your whole table and would delete any other entries. Once
installed, an entry submits jobs without you, so that step stays with
you.

With the Running automatically section of CLAUDE_example.md in
~/.claude/CLAUDE.md, a request such as one of these:

```
vclaude "run this folder automatically"
vclaude "set up scrontab for the auto agent every 5 hours with batch 20 and queue limit 30"
vclaude "run only the C11 folders automatically every hour"
```

returns the numbered steps with your folder filled in: check the
email settings, run one cycle by hand, open scrontab -e and paste a
seven line block, check with scrontab -l and squeue, watch the log,
and remove the block when AUTO_DONE appears. The block has the shape
shown in 05_auto_agent_scrontab.md, with your batch, limit, interval,
and path patterns. Replace $HOME in it with the output of
echo $HOME, and YOUR_ACCOUNT with your project if Claude did not ask.

Check the block before pasting it, the same way you read a preview
before typing yes.

More requests that work well:

```
vclaude "write a report and tell me which folders need attention"
vclaude "which folders crashed and why"
vclaude "give me the command to fix SCF failures with ALGO Normal and NELM 300"
vclaude "give me the command to submit the next 10 new jobs in C44"
```

## Cost

| Run | Cost |
|---|---|
| first try, auto model, Claude reading OUTCAR files itself | about 0.50 USD and 3 minutes for one folder |
| status, Sonnet, CLAUDE.md without syntax | 0.0345 USD |
| submit or edit suggestion, Sonnet, CLAUDE.md with syntax | 0.015 USD |

The cost shown is an estimate by Claude Code. The real bill is on
the Console.

## Why Claude never submits or edits

These commands change files or start jobs, and they wait for a typed
yes. In -p mode nobody can type it, and piping yes in would remove
the one safety rule the tool is built on. So Claude reads and
advises; you act.

The scheduled auto agent does not use Claude either. Submitting new
jobs until a queue limit is a fixed rule. An LLM call every cycle
would add cost and could read the same request differently from one
run to the next.
