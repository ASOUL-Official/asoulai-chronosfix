#!/usr/bin/env bash
set -euo pipefail

# Install the pinned AgentTeams embedded runtime in an isolated local profile.
# The installer is fetched from an immutable commit and never writes secrets to this repository.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_COMMIT="223ddc2b8073e4c8b93bcbb15e1d717f196c04d9"
INSTALLER_URL="https://raw.githubusercontent.com/agentscope-ai/AgentTeams/${SOURCE_COMMIT}/install/agentteams-install.sh"

if [[ -z "${AGENTTEAMS_LLM_API_KEY:-}" ]]; then
  echo 'AGENTTEAMS_LLM_API_KEY is required; set it in this shell and do not commit or paste it.' >&2
  exit 2
fi
command -v docker >/dev/null 2>&1 || { echo 'docker is required.' >&2; exit 2; }
docker version >/dev/null 2>&1 || { echo 'Docker Engine is not reachable.' >&2; exit 2; }
command -v curl >/dev/null 2>&1 || { echo 'curl is required.' >&2; exit 2; }

export AGENTTEAMS_NON_INTERACTIVE="${AGENTTEAMS_NON_INTERACTIVE:-1}"
export AGENTTEAMS_VERSION="${AGENTTEAMS_VERSION:-v1.2.3}"
export AGENTTEAMS_LLM_PROVIDER="${AGENTTEAMS_LLM_PROVIDER:-qwen}"
export AGENTTEAMS_DEFAULT_MODEL="${AGENTTEAMS_DEFAULT_MODEL:-qwen3.6-plus}"
export AGENTTEAMS_LOCAL_ONLY="${AGENTTEAMS_LOCAL_ONLY:-1}"
export AGENTTEAMS_DATA_DIR="${AGENTTEAMS_DATA_DIR:-$HOME/chronosfix-agentteams-data}"
export AGENTTEAMS_WORKSPACE_DIR="${AGENTTEAMS_WORKSPACE_DIR:-$HOME/chronosfix-agentteams-manager}"

# Keep the official runtime away from any other local AgentTeams deployment.
export AGENTTEAMS_GATEWAY_PORT="${AGENTTEAMS_GATEWAY_PORT:-28080}"
export AGENTTEAMS_CONSOLE_PORT="${AGENTTEAMS_CONSOLE_PORT:-28001}"
export AGENTTEAMS_ELEMENT_PORT="${AGENTTEAMS_ELEMENT_PORT:-28088}"
export AGENTTEAMS_MANAGER_PORT="${AGENTTEAMS_MANAGER_PORT:-28888}"
export AGENTTEAMS_DASHBOARD_PORT="${AGENTTEAMS_DASHBOARD_PORT:-23000}"

installer="$(mktemp "${TMPDIR:-/tmp}/agentteams-install.XXXXXX.sh")"
trap 'rm -f "$installer"' EXIT
curl --fail --location --retry 3 --silent --show-error "$INSTALLER_URL" -o "$installer"
test -s "$installer"
bash "$installer"

printf 'AgentTeams v1.2.3 installed from commit %s\n' "$SOURCE_COMMIT"
printf 'Data directory: %s\n' "$AGENTTEAMS_DATA_DIR"
printf 'Workspace directory: %s\n' "$AGENTTEAMS_WORKSPACE_DIR"
printf 'Element URL: http://127.0.0.1:%s/#/login\n' "$AGENTTEAMS_ELEMENT_PORT"
printf 'Next step: bash "%s/apply_resources.sh"\n' "$SCRIPT_DIR"
