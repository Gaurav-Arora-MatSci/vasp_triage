# vclaude: ask about vasp_triage in plain English through Claude Code.
# Add to ~/.bashrc with:
#   cat ~/vasp_triage/examples/templates/vclaude.sh >> ~/.bashrc
#   source ~/.bashrc
# Use from inside a calculation folder:
#   vclaude "check the status of this folder"
#   vclaude "run all jobs in this folder, check every 20 minutes"
#   vclaude_yes
# vclaude may run only vtriage status, report, and schedule. schedule
# only shows a plan and installs nothing. For edit and submit it
# prints the command for you to run.
# vclaude_yes continues the last vclaude answer in the same folder and
# may run vtriage confirm, which installs that plan. Run it right
# after vclaude, in the same folder, with no other claude call in
# between.

# Print the answer and the cost of the last call.
vclaude_print() {
    python3 -c "
import json
d = json.load(open('/tmp/vclaude_$USER.json'))
print(d.get('result', 'No answer. The run was stopped or failed.'))
print()
print('Cost: %.4f USD' % d.get('total_cost_usd', 0.0))
" 2>/dev/null || echo "No answer. The run was stopped or failed."
}

vclaude() {
    claude -p "$1" \
        --model sonnet \
        --allowedTools "Bash(vtriage status),Bash(vtriage status *),Bash(vtriage report),Bash(vtriage report *),Bash(vtriage schedule),Bash(vtriage schedule *)" \
        --append-system-prompt "Use the vtriage tool. Run vtriage status or vtriage report yourself when needed. For a request to submit or run the not submitted jobs, to run all jobs, to run automatically, or to check on an interval, run vtriage schedule with the options asked for, show the plan, and tell the user to run vclaude_yes to install it. Never run vtriage confirm or unschedule. For vtriage edit, submit, history, or auto, do not run them. Print the exact command for the user to run instead. Never pipe yes into any command." \
        --output-format json > /tmp/vclaude_$USER.json
    vclaude_print
}

vclaude_yes() {
    claude -p --continue "${1:-yes}" \
        --model sonnet \
        --allowedTools "Bash(vtriage status),Bash(vtriage status *),Bash(vtriage confirm),Bash(vtriage confirm *)" \
        --append-system-prompt "The user confirms the schedule plan from your previous answer. Run the vtriage confirm command printed in that plan, exactly as printed, then summarize the result in a few lines. If your previous answer did not show a schedule plan, run nothing and say so. Never run any other command that changes files or submits jobs." \
        --output-format json > /tmp/vclaude_$USER.json
    vclaude_print
}
