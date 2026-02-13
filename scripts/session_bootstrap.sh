#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== PaperBot Session Bootstrap =="
echo "Repo: $ROOT_DIR"
echo

echo "-- 1) Branch and working tree --"
git status --short --branch || true
echo

echo "-- 2) Recent commits --"
git log --oneline -20 || true
echo

echo "-- 3) Pending issue contracts --"
if [[ -f docs/issue_contract.json ]]; then
  python - <<'PY'
import json
from pathlib import Path

p = Path("docs/issue_contract.json")
try:
    data = json.loads(p.read_text())
except Exception as exc:
    print("failed to read {}: {}".format(p, exc))
    raise SystemExit(0)

items = data.get("issues", [])
open_items = [
    x for x in items if str(x.get("status", "")).lower() not in {"done", "closed"}
]
print("total issues in contract: {}".format(len(items)))
print("remaining issues: {}".format(len(open_items)))
for row in open_items[:10]:
    print("- #{} [{}] {}".format(row.get("id"), row.get("status", "unknown"), row.get("title", "")))
if len(open_items) > 10:
    print("... and {} more".format(len(open_items) - 10))
PY
else
  echo "docs/issue_contract.json not found"
fi
echo

echo "-- 4) Progress handoff tail --"
if [[ -f docs/progress/progress.txt ]]; then
  tail -n 80 docs/progress/progress.txt
else
  echo "docs/progress/progress.txt not found"
fi
echo

echo "-- 5) Suggested smoke checks --"
echo "python -m py_compile src/paperbot/api/routes/research.py"
echo "(cd web && ./node_modules/.bin/tsc --noEmit)"
echo

echo "Bootstrap complete."
