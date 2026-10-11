#!/usr/bin/env bash
# afterFileEdit (notification-only): format the edited Python file if ruff is
# installed, and warn on employer-data / secret patterns.
# It can't block the edit; CI's no-employer-data job is the real gate.
# Employer terms are checked by scripts/scan_blocked_terms.py against the hashed
# list in .github/blocked-terms.sha256. Every file is checked; there are no
# exempt paths. A scanner error (e.g. missing hash file) also warns.
set -uo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
f="$(python3 -c 'import sys,json; print(json.load(sys.stdin).get("file_path",""))')"
[ -f "$f" ] || exit 0
case "$f" in
  *.py) command -v ruff >/dev/null && ruff format -q "$f" && ruff check -q --fix "$f" ;;
esac
python3 - "$f" <<'PY'
import re
import sys

text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
secret = re.compile(
    r"BEGIN (RSA|OPENSSH) PRIVATE KEY|xai-[A-Za-z0-9]{20,}",
    re.I,
)
sys.exit(2 if secret.search(text) else 0)
PY
status=$?
if [ "$status" -eq 0 ] && ! python3 "$root/scripts/scan_blocked_terms.py" "$f" >/dev/null 2>&1; then
  status=2
fi
if [ "$status" -ne 0 ]; then
  mkdir -p .cursor/hook-logs
  echo "$(date -u +%FT%TZ) WARN employer/secret pattern in $f" >> .cursor/hook-logs/warnings.log
fi
exit 0
