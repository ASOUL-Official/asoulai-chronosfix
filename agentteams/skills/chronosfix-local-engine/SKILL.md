---
name: chronosfix-local-engine
description: Run the deterministic ChronosFix incident-to-PR evidence pipeline and return auditable run, gate and artifact metadata.
---

# ChronosFix Local Engine

Use this Skill when an incident scenario must be replayed through the ChronosFix local engineering kernel.

## Preconditions

- Work only inside the mounted ChronosFix repository.
- Treat scenario data as synthetic unless the Human explicitly supplies an approved real dataset.
- Never pass credentials on the command line.

## Execution

For analysis without release approval:

```bash
python agentteams/run_chronosfix_team.py \
  --scenario scenarios/checkout-timeout/scenario.json \
  --output output/agentteams-runtime
```

For a quality-passing medium/high-risk result, a Human must provide a name and reason:

```bash
python agentteams/run_chronosfix_team.py \
  --scenario scenarios/checkout-timeout/scenario.json \
  --output output/agentteams-runtime \
  --approve \
  --approver "AsoulAI Release Owner" \
  --approval-reason "Reviewed deterministic replay and rollback evidence"
```

## Required return fields

- `run_id`
- `trace_id`
- `quality_gate`
- `release_decision`
- `selected_patch`
- `run-manifest.json`
- `github-pr-checks.json`

## Safety rules

- `blocked-quality-gate` cannot be overridden by a Human.
- `blocked-awaiting-human` means quality passed but a named approval is missing.
- The generated GitHub files are local drafts unless a separate authorized GitHub adapter performs the write.
- If AgentTeams Controller/Matrix did not execute the task, label the transcript as compatible mapping evidence.
