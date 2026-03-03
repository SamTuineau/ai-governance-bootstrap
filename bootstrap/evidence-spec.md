# Evidence Specification (Minimal, Universal)

This document defines the minimal evidence schema used by governed projects.

It enforces **LAW 3 — Evidence-Based Completion** from `../constitution/AI_ENGINEERING_CONSTITUTION.md` by making completion claims auditable.

## Evidence Entry Schema (Minimal)
An evidence entry is a single JSON object with the following required fields:

- `timestamp` (string, ISO-8601 UTC): When the evidence was produced.
- `phase` (string): Bootstrap phase identifier (e.g., `phase-2`) or task lifecycle step (e.g., `verify`).
- `action` (string): What was attempted (e.g., `probe_command_executable`, `check_file_presence`).
- `input` (object | string | null): Parameters used (paths, command string, target identifiers).
- `result` (object | string): Output summary sufficient to re-check or reproduce.
- `confidence` (string): One of `high`, `medium`, `low`.
- `source` (string): Where the evidence came from (e.g., `repo_scan`, `command_output`, `human_confirmation`).

### Optional fields (allowed)
- `law` (string): Related constitution law (e.g., `LAW 3`).
- `rule_id` (string): Related guardrail id (e.g., `VER-001`).
- `artifacts` (array): Paths to stored outputs under `.governance/evidence/`.
- `notes` (string): Additional context.

## Storage Format
Evidence must be stored in the governed project under:
- `.governance/evidence/`

Recommended minimal implementation:
- `.governance/evidence/evidence.jsonl` (newline-delimited JSON entries; append-only)

Projects may add additional evidence files, but must not remove required fields from entries.

## JSON Example
```json
{
  "timestamp": "2026-02-26T08:55:10Z",
  "phase": "phase-2",
  "action": "command_executable",
  "input": {
    "command": "<project-defined verification command>",
    "mode": "help_or_dry_run"
  },
  "result": {
    "exit_code": 0,
    "summary": "Command resolved and executed successfully",
    "output_excerpt": "<first N characters>"
  },
  "confidence": "high",
  "source": "command_output",
  "law": "LAW 3",
  "rule_id": "VER-001",
  "artifacts": [
    ".governance/evidence/2026-02-26_phase-2_command-executable.txt"
  ]
}
```

## Evidence Immutability Rules
Evidence is an audit trail.

- Evidence records are **append-only**.
- Do not edit or delete existing evidence entries.
- If an entry is wrong or incomplete, add a new entry that:
  - references the prior entry (via `notes`)
  - provides corrected inputs/results
  - explains why confidence changed

## LAW 3 Linkage (Required)
Any completion claim must be traceable to evidence entries that demonstrate:
- what was checked,
- what inputs were used,
- what the result was,
- and why the agent is confident.

If evidence cannot be produced, the agent must not claim completion and must record the missing evidence as an explicit gap.
