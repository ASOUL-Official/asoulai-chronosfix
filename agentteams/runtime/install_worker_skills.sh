#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
MANAGER_WORKSPACE="${AGENTTEAMS_WORKSPACE_DIR:-/root/agentteams-manager}"
UPSTREAM_DIR="${AGENTTEAMS_SKILL_SOURCE_DIR:-/root/alibabacloud-aiops-skills}"
UPSTREAM_REPO="https://github.com/aliyun/alibabacloud-aiops-skills.git"
UPSTREAM_COMMIT="4dc1013ec2564f85fd07e5b5945b2d34ceca7eff"

if [[ ! -d "${UPSTREAM_DIR}/.git" ]]; then
  git clone "${UPSTREAM_REPO}" "${UPSTREAM_DIR}"
fi
git -C "${UPSTREAM_DIR}" fetch --depth 1 origin "${UPSTREAM_COMMIT}"
git -C "${UPSTREAM_DIR}" checkout --detach "${UPSTREAM_COMMIT}"

install -d "${MANAGER_WORKSPACE}/worker-skills/chronosfix-local-engine"
cp -a "${REPO_ROOT}/agentteams/skills/chronosfix-local-engine/." \
  "${MANAGER_WORKSPACE}/worker-skills/chronosfix-local-engine/"

install -d "${MANAGER_WORKSPACE}/worker-skills/alibabacloud-sls-query"
cp -a "${UPSTREAM_DIR}/skills/storage/sls/alibabacloud-sls-query/." \
  "${MANAGER_WORKSPACE}/worker-skills/alibabacloud-sls-query/"

printf 'Installed Worker Skills into %s\n' "${MANAGER_WORKSPACE}/worker-skills"
printf 'Official Skill source commit: %s\n' "${UPSTREAM_COMMIT}"
