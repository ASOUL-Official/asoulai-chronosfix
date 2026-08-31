#!/usr/bin/env bash
set -euo pipefail

# Verify the real Controller and the v1beta1 resources without exposing secrets.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUTPUT_DIR="${1:-${REPO_ROOT}/evidence/agentteams-official-runtime}"
CONTROLLER="${AGENTTEAMS_CONTROLLER_CONTAINER:-agentteams-controller}"

command -v docker >/dev/null 2>&1 || { echo 'docker is required.' >&2; exit 2; }
if ! docker ps --format '{{.Names}}' | grep -qx "$CONTROLLER"; then
  echo "${CONTROLLER} is not running; install the pinned AgentTeams runtime first." >&2
  exit 2
fi

mkdir -p "$OUTPUT_DIR"
docker inspect --format '{{json .State}}' "$CONTROLLER" > "${OUTPUT_DIR}/controller-state.json"
docker exec "$CONTROLLER" agt get managers -o json > "${OUTPUT_DIR}/managers.json"
docker exec "$CONTROLLER" agt get workers -o json > "${OUTPUT_DIR}/workers.json"
docker exec "$CONTROLLER" agt get teams -o json > "${OUTPUT_DIR}/teams.json"
docker exec "$CONTROLLER" agt get humans -o json > "${OUTPUT_DIR}/humans.json"

python3 - "$OUTPUT_DIR" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
required = ["managers.json", "workers.json", "teams.json", "humans.json"]
for name in required:
    payload = json.loads((root / name).read_text(encoding="utf-8"))
    if not isinstance(payload, (dict, list)):
        raise SystemExit(f"invalid agt output: {name}")
summary = {
    "schema": "chronosfix.agentteams-official-runtime/v1",
    "controller_container": "agentteams-controller",
    "resource_queries": required,
    "secrets_included": False,
}
(root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
PY
