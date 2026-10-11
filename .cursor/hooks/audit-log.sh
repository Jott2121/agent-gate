#!/usr/bin/env bash
# stop hook: append one JSONL receipt per agent session (status + branch + HEAD + diffstat).
set -uo pipefail
payload="$(cat)"
mkdir -p .cursor/hook-logs
python3 - "$payload" <<'PY' >> .cursor/hook-logs/sessions.jsonl
import json,subprocess,sys,datetime
p=json.loads(sys.argv[1] or "{}")
g=lambda *a: subprocess.run(["git",*a],capture_output=True,text=True).stdout.strip()
print(json.dumps({"ts":datetime.datetime.utcnow().isoformat()+"Z","status":p.get("status"),
  "conversation_id":p.get("conversation_id"),"branch":g("rev-parse","--abbrev-ref","HEAD"),
  "head":g("rev-parse","--short","HEAD"),"diffstat":g("diff","--shortstat")}))
PY
exit 0
