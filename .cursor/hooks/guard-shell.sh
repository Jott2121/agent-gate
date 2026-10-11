#!/usr/bin/env bash
# beforeShellExecution guard. Reads {"command": "...", "cwd": "..."} on stdin.
# Denies irreversible / publishing commands; asks on network fetches. Fails closed (hooks.json failClosed: true).
set -euo pipefail
input="$(cat)"
# Invalid JSON exits non-zero (fail closed via hooks.json failClosed).
# A well-formed payload with a missing, blank, or non-string command is denied below.
if ! cmd="$(printf '%s' "$input" | python3 -c 'import json,sys
try:
    data=json.load(sys.stdin)
except json.JSONDecodeError:
    raise SystemExit(1)
if not isinstance(data, dict):
    raise SystemExit(0)
command=data.get("command")
sys.stdout.write(command if isinstance(command, str) else "")')"; then
  exit 1
fi
deny() { printf '{"permission":"deny","user_message":"%s","agent_message":"%s Open a PR instead; a human will do this step."}\n' "$1" "$1"; exit 0; }
ask()  { printf '{"permission":"ask","user_message":"%s"}\n' "$1"; exit 0; }
if [ -z "${cmd//[[:space:]]/}" ]; then
  deny "Shell guard blocked a missing command."
fi
case "$cmd" in
  *"push --force"*|*"push -f"*|*"--force-with-lease"*|*"git push"*"--force"*|*"git push"*" -f"*) deny "Force-push blocked by repo policy." ;;
  *"reset --hard"*|*"rebase"*)                        deny "History rewrite blocked by repo policy." ;;
  *"git tag"*|*"twine upload"*|*"uv publish"*|*"gh release"*) deny "Releases/publishing are human-only." ;;
  *"rm -rf /"*|*"rm -rf ~"*|*'rm -rf $HOME'*)         deny "Destructive delete blocked." ;;
  *"curl"*"| sh"*|*"curl"*"| bash"*|*"wget"*"| sh"*|*"wget"*"| bash"*) deny "Pipe-to-shell blocked." ;;
  *"git push"*)                                       ask  "Agent wants to push a branch. Allow?" ;;
  *"curl"*|*"wget"*)                                  ask  "Agent wants network access: $cmd" ;;
esac
printf '{"permission":"allow"}\n'
