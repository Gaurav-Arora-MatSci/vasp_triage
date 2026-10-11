# vclaude: ask about vasp_triage in plain English through Claude Code.
# Add to ~/.bashrc with:
#   cat ~/vasp_triage/examples/templates/vclaude.sh >> ~/.bashrc
#   source ~/.bashrc
# Use from inside a calculation folder:
#   vclaude "check the status of this folder"
# Claude may run only vtriage status and vtriage report. For edit and
# submit it prints the command for you to run.

vclaude() {
    claude -p "$1" \
        --model sonnet \
        --allowedTools "Bash(vtriage status),Bash(vtriage status *),Bash(vtriage report),Bash(vtriage report *)" \
        --append-system-prompt "Use the vtriage tool. Run vtriage status or vtriage report yourself when needed. For vtriage edit, submit, or history, do not run them. Print the exact command for the user to run instead. Never pipe yes into any command." \
        --output-format json > /tmp/vclaude_$USER.json
    python3 -c "
import json
d = json.load(open('/tmp/vclaude_$USER.json'))
print(d.get('result', 'No answer. The run was stopped or failed.'))
print()
print('Cost: %.4f USD' % d.get('total_cost_usd', 0.0))
" 2>/dev/null || echo "No answer. The run was stopped or failed."
}
