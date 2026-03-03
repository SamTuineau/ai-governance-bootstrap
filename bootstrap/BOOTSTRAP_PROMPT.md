**Bootstrap Identity Requirement:**

Before executing, the agent MUST read BOOTSTRAP_IDENTITY.md
and confirm this governance system applies to engineering workflow governance,
not organizational AI governance.

# Bootstrap Protocol (Deterministic)

This document defines the exact protocol an agent executes to initialize governance in a new project.

**Non-negotiable bootstrap rule:** bootstrap may create or modify **governance artifacts only**. It must **not** modify application/product code, dependency graphs, runtime infrastructure, or deployment state.

Governance principles are defined in `../constitution/AI_ENGINEERING_CONSTITUTION.md`. Ongoing agent behavior is defined in `../agents/agent-behaviour.md`.

Governance version metadata is defined in `../governance-version.json` and must be recorded inside governed projects as `.governance/governance-version.json`.
Evidence must follow the minimal schema defined in `evidence-spec.md`.

The evidence specification (evidence-spec.md) must be vendored into the governed project's .governance/ directory during bootstrap.

## Phase 0 — Invocation Rules
**Goals**
- Establish that this run is a governance bootstrap.
- Prevent accidental application changes.

**Allowed actions**
- Read-only inspection of the repository and environment.
- Create governance directories and documents.
- Run non-destructive discovery commands (version checks, help output, listing capabilities) when available.

**Outputs created**
- A bootstrap session identifier (recorded in the Governance Status Report; see Phase 7).

**Required files**
- `../constitution/AI_ENGINEERING_CONSTITUTION.md`
- `../agents/agent-behaviour.md`
- `../governance-version.json`

## Phase 1 — Project Interrogation
**Goals**
- Capture repository reality: languages, structure, signals, constraints.
- Minimize human questions.

**Allowed actions**
- Read files, list directories, search for known repo signals.
- Ask humans only when required (see interrogation policy).

**Outputs created**
- `.governance/project-profile.json` (schema defined in `./project-interrogation.md`)

**Required files**
- `./project-interrogation.md`

## Phase 2 — Environment Discovery
**Goals**
- Determine whether the environment can safely run validations and edits.
- Establish baseline “doctor checks” inputs.

**Allowed actions**
- Non-destructive discovery commands (e.g., “is command executable”, “list versions”).
- Read-only inspection of environment configuration files present in repo.

**Outputs created**
- Evidence records recorded under `.governance/evidence/` following `evidence-spec.md`.

**Required files**
- `../guardrails/validation-patterns.yaml`
- `evidence-spec.md`

## Phase 3 — System Manifest Creation
**Goals**
- Create a stack-neutral manifest describing what exists and how it should be validated.

**Allowed actions**
- Write new governance files under `.governance/` only.
- Derive manifest contents from `.governance/project-profile.json` plus observed repo signals.

**Outputs created**
- `.governance/governance-version.json` (copied from `../governance-version.json`)
- `.governance/system-manifest.json` containing, at minimum:
	- project identity (name, repo root)
	- detected languages and dependency manager signals
	- known entrypoints and automation signals (CI, scripts)
	- verification hooks (how to run “doctor checks”, test/validation commands if present)
	- constraints and unknowns

**Required files**
- `.governance/project-profile.json` (from Phase 1)
- `../governance-version.json`

## Phase 4 — Guardrail Installation
**Goals**
- Install baseline guardrails and validation patterns for this project.

**Allowed actions**
- Copy or vendor governance configuration into `.governance/guardrails/`.
- Parameterize guardrails using manifest/profile (without stack assumptions).

**Outputs created**
- `.governance/guardrails/baseline-rules.yaml` (sourced from `../guardrails/baseline-rules.yaml`)
- `.governance/guardrails/validation-patterns.yaml` (sourced from `../guardrails/validation-patterns.yaml`)

**Required files**
- `../guardrails/baseline-rules.yaml`
- `../guardrails/validation-patterns.yaml`

## Phase 5 — Task Governance Activation
**Goals**
- Make governance the default operating mode for subsequent agent work.

**Allowed actions**
- Write governance instructions for agents into `.governance/`.
- Declare the required execution lifecycle (see `../agents/agent-behaviour.md`).

**Outputs created**
- `.governance/agent-runtime.md` containing:
	- mandatory lifecycle: Interrogate → Validate → Plan → Execute → Verify → Learn
	- required “doctor checks” before changes
	- evidence requirements before completion
	- refusal criteria for unsafe actions

Bootstrap must also copy the following runtime governance artifacts into the governed project’s `.governance/` directory:
- `governance-version.json`
- `capability-registry.md`
- `session-start.md`
- `evidence-spec.md`

These artifacts ensure governance operates independently of the bootstrap repository.

**Required files**
- `../agents/agent-behaviour.md`
- `.governance/system-manifest.json`

## Phase 6 — Learning System Initialization
**Goals**
- Enable controlled evolution through persistent incident/proposal records.

**Allowed actions**
- Create learning directories and templates under `.governance/learning/`.
- Seed templates (without changing existing application files).

**Outputs created**
- `.governance/learning/incidents/` directory
- `.governance/learning/proposals/` directory
- `.governance/learning/README.md` summarizing the lifecycle (as defined in `../learning/lessons-schema.md`).

**Required files**
- `../learning/lessons-schema.md`

## Phase 7 — Governance Status Report
**Goals**
- Provide a deterministic, reviewable report that bootstrap completed correctly.

**Allowed actions**
- Summarize actions and evidence.
- Reference created artifacts and any open unknowns.

**Outputs created**
- `.governance/status.md` containing:
	- bootstrap session id and timestamp
	- list of created governance files
	- interrogation summary (derived from project profile)
	- environment discovery summary (doctor check readiness)
	- verification/evidence summary (referencing evidence entries recorded per `evidence-spec.md`)
	- explicit statement: “No application code was modified during bootstrap.”

**Required files**
- `.governance/project-profile.json`
- `.governance/system-manifest.json`

## Explicit Prohibitions (Bootstrap)
- Do not modify application or product code.
- Do not add, remove, or update dependencies.
- Do not run destructive commands.
- Do not mutate runtime infrastructure or deployments.
- Do not introduce stack assumptions.

## Final Success Criteria
Bootstrap is successful only when all are true:
- `.governance/project-profile.json` exists and matches the schema in `./project-interrogation.md`.
- `.governance/governance-version.json` exists and reflects `../governance-version.json`.
- `.governance/system-manifest.json` exists and references verification hooks.
- Baseline guardrails and validation patterns are installed under `.governance/guardrails/`.
- Learning directories exist under `.governance/learning/`.
- `.governance/status.md` exists and includes evidence summaries.
- Evidence supports completion claims (see `../constitution/AI_ENGINEERING_CONSTITUTION.md`, LAW 3).
