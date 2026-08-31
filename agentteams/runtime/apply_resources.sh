#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="${SCRIPT_DIR}/chronosfix-resources.yaml"
AGENTTEAMS_SOURCE_DIR="${AGENTTEAMS_SOURCE_DIR:-/root/agentteams-src}"

# Reuse the isolated workspace selected by install_official_local.sh.
RUNTIME_ENV_FILE="${AGENTTEAMS_RUNTIME_ENV_FILE:-${AGENTTEAMS_DATA_DIR:-$HOME/chronosfix-agentteams-data}/chronosfix-runtime.env}"
if [[ -f "$RUNTIME_ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$RUNTIME_ENV_FILE"
fi

python3 "${SCRIPT_DIR}/validate_resources.py" "${MANIFEST}"
"${SCRIPT_DIR}/install_worker_skills.sh"

if ! docker ps --format '{{.Names}}' | grep -qx 'agentteams-controller'; then
  echo 'agentteams-controller is not running; install AgentTeams v1.2.3 first.' >&2
  exit 2
fi

bash "${AGENTTEAMS_SOURCE_DIR}/install/agentteams-apply.sh" -f "${MANIFEST}"
docker exec agentteams-controller agt get workers -o json
docker exec agentteams-controller agt get teams -o json
docker exec agentteams-controller agt get humans -o json
