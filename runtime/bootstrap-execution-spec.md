# Bootstrap Execution Specification (Executable, Stack-Neutral)

## Purpose
This document translates the deterministic bootstrap protocol in `../bootstrap/BOOTSTRAP_PROMPT.md` into an **executable specification** suitable for automation.

It does **not** change governance philosophy, phases, laws, or prohibitions. In any conflict, the source protocol remains authoritative.

## Authoritative Inputs (Source of Truth)
Bootstrap execution MUST be derived from and remain consistent with:
- Bootstrap protocol: `../bootstrap/BOOTSTRAP_PROMPT.md`
- Bootstrap identity constraints: `../bootstrap/BOOTSTRAP_IDENTITY.md`
- Constitution: `../constitution/AI_ENGINEERING_CONSTITUTION.md`
- Agent runtime contract: `../agents/agent-behaviour.md`, `../agents/session-start.md`, `../agents/capability-registry.md`
- Guardrails + validation patterns: `../guardrails/baseline-rules.yaml`, `../guardrails/validation-patterns.yaml`
- Evidence schema: `../bootstrap/evidence-spec.md`
- Governance version metadata: `../governance-version.json`

## Determinism Requirements
An automated bootstrap implementation MUST be deterministic with respect to:
- repo file state at invocation time
- environment discovery outputs recorded as evidence
- explicit human answers (only when required)

A deterministic implementation MUST:
- record inputs used for each decision (repo signals, command probes)
- record outputs produced (created files + evidence entries)
- refuse prohibited actions rather than attempting them

## Stack Neutrality Requirements
- Bootstrap MUST NOT assume a language, build tool, test runner, CI provider, or container platform.
- Validation MUST be expressed via patterns in `../guardrails/validation-patterns.yaml` and parameterized by observed repo signals.

## Scope Boundary (Non-Negotiable)
Bootstrap MAY create/modify **governance artifacts only**.
Bootstrap MUST NOT modify:
- application/product code
- dependency graphs
- runtime infrastructure
- deployment state

## Evidence Recording (Universal)
Evidence MUST be recorded under `.governance/evidence/` using the schema in `.governance/evidence-spec.md` (vendored from `../bootstrap/evidence-spec.md`).

Minimum recommended evidence store:
- `.governance/evidence/evidence.jsonl` (append-only)

Evidence entries MUST include, at minimum:
- `phase` as `phase-0`..`phase-7`
- `action` describing the check performed
- `input` describing parameters (paths, commands)
- `result` summarizing outputs (exit code, discovered signals)
- `confidence` and `source`

---

# Phase Specifications

## Phase 0 — Invocation Rules
### Inputs
- Repository root path (invocation context)
- Bootstrap identity confirmation (must read identity doc)
- Governance version metadata from `../governance-version.json`

### Outputs
- A bootstrap session identifier (unique string)

### Files Created
- No files are required to be created in Phase 0.

### Validation Checks
- Confirm bootstrap identity scope:
  - Must be **engineering workflow governance**, not enterprise risk/compliance governance.
- Confirm allowed action boundary:
  - Only `.governance/` artifacts will be created/modified.
- Confirm authoritative documents are readable:
  - `../constitution/AI_ENGINEERING_CONSTITUTION.md`
  - `../agents/agent-behaviour.md`
  - `../governance-version.json`

### Evidence Recorded
- `phase-0`: record session id generation method and the scope boundary confirmation.
- `phase-0`: record presence/readability of required files.

### Failure Conditions
- Identity mismatch (organizational governance outputs requested or implied) → STOP.
- Any required file unreadable → STOP.
- Any request to modify non-governance artifacts during bootstrap → STOP.

---

## Phase 1 — Project Interrogation
### Inputs
- Repository file tree and contents (read-only inspection)
- Interrogation rules and conceptual schema from `./project-interrogation.md`

### Outputs
- Project profile capturing repo reality

### Files Created
- `.governance/project-profile.json`

### Validation Checks
- Follow interrogation operating rules:
  - Prefer auto-detection from repo signals.
  - Ask humans only when required for safe governance/verification.
- Detect and record (best-effort):
  - languages and evidence paths
  - dependency manager signals (manifest + lockfiles)
  - CI presence + definition paths
  - containerization signals (without assuming requirement)
  - runtime clues (version pins, env templates, automation scripts)
  - constraints (protected paths, required confirmations)
  - unknowns list

### Evidence Recorded
- `phase-1`: evidence entries for each detection category:
  - file presence/path evidence
  - summary of detection results + confidence
  - any human answers (source=`human_confirmation`)

### Failure Conditions
- Repo root cannot be inspected (permissions/read failures) → STOP.
- Required interrogation output cannot be written under `.governance/` → STOP.
- Critical unknown remains unresolved and blocks safe governance initialization → STOP and ask minimal questions.

---

## Phase 2 — Environment Discovery
### Inputs
- Validation patterns from `../guardrails/validation-patterns.yaml`
- Observed repo automation signals and manifest hints (from Phase 1)

### Outputs
- Evidence records establishing readiness for non-destructive validation and governance file edits

### Files Created
- `.governance/evidence/*` (at minimum `.governance/evidence/evidence.jsonl`)

### Validation Checks
- Run only non-destructive discovery probes, such as:
  - PAT-005 command executable checks for any discovered verification hooks (help/version/dry-run)
  - PAT-002 dependency installed checks (read-only detection)
  - PAT-003 configuration present/parseable checks (read-only parsing where possible)

### Evidence Recorded
- `phase-2`: command executable outputs, exit codes, and excerpts
- `phase-2`: file presence checks for configuration templates
- `phase-2`: readiness summary (what can/cannot be verified here)

### Failure Conditions
- Environment readiness cannot be established for the intended next steps → STOP and report missing prerequisites with evidence.
- Any probe would be destructive/installs dependencies/mutates infra → DO NOT RUN; record refusal and treat as blocked.

---

## Phase 3 — System Manifest Creation
### Inputs
- `.governance/project-profile.json`
- Governance version metadata from `../governance-version.json`
- Evidence from Phase 2 environment discovery

### Outputs
- A stack-neutral system manifest describing what exists and how to validate it

### Files Created
- `.governance/governance-version.json` (copy of `../governance-version.json`)
- `.governance/system-manifest.json`

### Validation Checks
- Confirm `.governance/project-profile.json` exists (from Phase 1).
- Create `.governance/system-manifest.json` containing, at minimum:
  - project identity (name, repo root)
  - detected languages and dependency manager signals
  - known entrypoints and automation signals (CI, scripts)
  - verification hooks (how to run doctor checks; any discovered test/validation commands if present)
  - constraints and unknowns

### Evidence Recorded
- `phase-3`: evidence entry referencing created/updated manifest artifacts and a summary of contents.

### Failure Conditions
- Attempt to infer tooling that is not evidenced by repo signals → STOP and record as stack-assumption risk.
- Required manifest minimum fields cannot be populated from evidence → STOP and record unknowns.

---

## Phase 4 — Guardrail Installation
### Inputs
- Guardrails from `../guardrails/baseline-rules.yaml`
- Validation patterns from `../guardrails/validation-patterns.yaml`
- `.governance/system-manifest.json`

### Outputs
- Project-local guardrails and validation patterns installed under `.governance/guardrails/`

### Files Created
- `.governance/guardrails/baseline-rules.yaml`
- `.governance/guardrails/validation-patterns.yaml`

### Validation Checks
- Confirm vendored files are exact copies or explicitly parameterized without changing meanings.
- Confirm portability note is satisfied (no repository-relative paths assumed).

### Evidence Recorded
- `phase-4`: evidence entry listing installed guardrail files and their source paths.

### Failure Conditions
- Any change would alter the semantics of baseline rules/patterns (not just vendoring/parameterization) → STOP.

---

## Phase 5 — Task Governance Activation
### Inputs
- Agent behavior contract: `../agents/agent-behaviour.md`
- Session start contract: `../agents/session-start.md`
- Capability registry: `../agents/capability-registry.md`
- Evidence spec: `../bootstrap/evidence-spec.md`
- `.governance/system-manifest.json`

### Outputs
- Governance becomes the default runtime mode for subsequent agent work in the governed project

### Files Created
- `.governance/agent-runtime.md`
- `.governance/governance-version.json` (already created in Phase 3, must exist)
- `.governance/capability-registry.md` (vendored)
- `.governance/session-start.md` (vendored)
- `.governance/evidence-spec.md` (vendored)

### Validation Checks
- `.governance/agent-runtime.md` MUST include:
  - lifecycle: Interrogate → Validate → Plan → Execute → Verify → Learn
  - doctor check requirement before changes
  - evidence requirement before completion
  - refusal criteria for unsafe actions

### Evidence Recorded
- `phase-5`: evidence entry listing vendored runtime governance artifacts and confirming lifecycle inclusion.

### Failure Conditions
- Any missing vendored runtime artifact → STOP.
- Any runtime instruction contradicts constitution/guardrails → STOP.

---

## Phase 6 — Learning System Initialization
### Inputs
- Learning lifecycle definition and templates from `../learning/lessons-schema.md`

### Outputs
- Controlled evolution directories and summary instructions in the governed project

### Files Created
- `.governance/learning/incidents/`
- `.governance/learning/proposals/`
- `.governance/learning/README.md`

### Validation Checks
- Learning README must summarize the required lifecycle:
  - Incident → Analysis → Guardrail Proposal → Human Approval → Governance Update
- Explicit prohibition must be preserved:
  - agents do not auto-mutate governance rules

### Evidence Recorded
- `phase-6`: evidence entry listing created learning directories/files.

### Failure Conditions
- Learning scaffolding cannot be created under `.governance/` → STOP.

---

## Phase 7 — Governance Status Report
### Inputs
- `.governance/project-profile.json`
- `.governance/system-manifest.json`
- Evidence records `.governance/evidence/*`

### Outputs
- Deterministic status report of what bootstrap did and what remains unknown

### Files Created
- `.governance/status.md`

### Validation Checks
- Status report MUST include:
  - session id and timestamp
  - list of created governance files
  - interrogation summary (from project profile)
  - environment discovery summary (readiness)
  - evidence summary referencing recorded evidence entries
  - explicit statement: "No application code was modified during bootstrap."

### Evidence Recorded
- `phase-7`: evidence entry that status report was created and references the summarized evidence set.

### Failure Conditions
- Missing required sections in status report → STOP and correct within governance-only scope.

---

# Validation Check A — Phase-to-Protocol Mapping (Required)

This executable specification maps directly to `../bootstrap/BOOTSTRAP_PROMPT.md` without introducing new phases or changing prohibitions.

## Mapping Table
- Phase 0 in this spec ↔ "Phase 0 — Invocation Rules" in `../bootstrap/BOOTSTRAP_PROMPT.md` (goals, allowed actions, session id output, required files)
- Phase 1 in this spec ↔ "Phase 1 — Project Interrogation" in `../bootstrap/BOOTSTRAP_PROMPT.md` (project-profile output; interrogation policy)
- Phase 2 in this spec ↔ "Phase 2 — Environment Discovery" in `../bootstrap/BOOTSTRAP_PROMPT.md` (doctor checks + evidence under `.governance/evidence/`)
- Phase 3 in this spec ↔ "Phase 3 — System Manifest Creation" in `../bootstrap/BOOTSTRAP_PROMPT.md` (vendored governance-version + system-manifest minimum fields)
- Phase 4 in this spec ↔ "Phase 4 — Guardrail Installation" in `../bootstrap/BOOTSTRAP_PROMPT.md` (vendoring baseline rules + validation patterns)
- Phase 5 in this spec ↔ "Phase 5 — Task Governance Activation" in `../bootstrap/BOOTSTRAP_PROMPT.md` (agent-runtime + vendored runtime artifacts list)
- Phase 6 in this spec ↔ "Phase 6 — Learning System Initialization" in `../bootstrap/BOOTSTRAP_PROMPT.md` (learning directories + learning README)
- Phase 7 in this spec ↔ "Phase 7 — Governance Status Report" in `../bootstrap/BOOTSTRAP_PROMPT.md` (status.md contents + explicit no-app-code statement)

## Explicit Prohibitions Mapping
All prohibitions in this spec are copied from the "Non-negotiable bootstrap rule" section and "Explicit Prohibitions (Bootstrap)" section of `../bootstrap/BOOTSTRAP_PROMPT.md`, and the identity non-goals/stop condition in `../bootstrap/BOOTSTRAP_IDENTITY.md`.

## Alignment Result (A)
PASS criteria for Phase A is met if:
- no new phases were introduced
- all required outputs listed in `../bootstrap/BOOTSTRAP_PROMPT.md` are preserved
- no additional allowed actions exceed the protocol (governance-only)
- evidence recording requirements remain consistent with `../bootstrap/evidence-spec.md`

(An automated implementation MUST treat the protocol as authoritative; this file is an execution-oriented restatement, not a replacement.)
