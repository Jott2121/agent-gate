#!/usr/bin/env bash
# afterFileEdit (notification-only): format the edited Python file if ruff is
# installed, and warn on employer-data / secret patterns.
# It can't block the edit; CI's no-employer-data job is the real gate.
# The README "## About" author bio is not a hit. Policy files that name the
# prohibition (.cursor/, AGENTS.md) are not employer-data hits either.
set -uo pipefail
f="$(python3 -c 'import sys,json; print(json.load(sys.stdin).get("file_path",""))')"
[ -f "$f" ] || exit 0
case "$f" in
  *.py) command -v ruff >/dev/null && ruff format -q "$f" && ruff check -q --fix "$f" ;;
esac
python3 - "$f" <<'PY'
import re
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8", errors="replace").read()
secret = re.compile(
    r"BEGIN (RSA|OPENSSH) PRIVATE KEY|xai-[A-Za-z0-9]{20,}",
    re.I,
)
employer = re.compile(
    r"lockheed|\blmco\b|\bCUI\b|ITAR|EXPORT CONTROLLED|PROPRIETARY",
    re.I,
)
if secret.search(text):
    sys.exit(2)

normalized = path.replace("\\", "/")
policy = (
    "/.cursor/" in f"/{normalized}"
    or normalized.endswith("/AGENTS.md")
    or normalized == "AGENTS.md"
)
if not policy and employer.search(text):
    if normalized.endswith("/README.md") or normalized == "README.md":
        lines = text.splitlines()
        start = None
        kept = []
        for line in lines:
            if start is None and line.startswith("## About"):
                start = True
                continue
            if start is True and line.startswith("## "):
                start = False
            if start is True:
                continue
            kept.append(line)
        if employer.search("\n".join(kept)):
            sys.exit(2)
    else:
        sys.exit(2)
sys.exit(0)
PY
status=$?
if [ "$status" -eq 2 ]; then
  mkdir -p .cursor/hook-logs
  echo "$(date -u +%FT%TZ) WARN employer/secret pattern in $f" >> .cursor/hook-logs/warnings.log
fi
exit 0
