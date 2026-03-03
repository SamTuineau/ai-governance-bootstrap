# One-Button Bootstrap Contract — `governance init`

## Purpose
This document defines the deterministic contract for a single invocation that initializes governance in a target repository.

It is constrained by the authoritative bootstrap protocol in `../bootstrap/BOOTSTRAP_PROMPT.md` and identity constraints in `../bootstrap/BOOTSTRAP_IDENTITY.md`.

## Authority and Version Linkage
- Governance version source of truth: `../governance-version.json`
- Governed project version record (output): `.governance/governance-version.json`

---

# 1) Invocation Requirements

## 1.1 Invocation Name
The one-button operation is conceptually: **`governance init`**.

## 1.2 Required Preconditions
Before running, the invoker (human or automation) MUST ensure:
- Repository is accessible (read/write permissions to create `.governance/`)
- The bootstrap implementation can perform read-only inspection of the repo
- The bootstrap implementation can record evidence under `.governance/evidence/`

## 1.3 Required Inputs
The invocation MUST have, at minimum:
- target repository root path
- access to bootstrap governance artifacts (this repository or an equivalent vendored distribution)

Optional inputs (only if needed and only when they do not introduce stack assumptions):
- explicit human answers to minimal interrogation questions (see `../bootstrap/project-interrogation.md`)

---

# 2) Expected Repository State Before Run

The target repository may be:
- not yet governed (no `.governance/` directory), or
- partially governed (some `.governance/*` exists), or
- governed but outdated governance version.

The contract does not require any specific language, build tool, CI provider, container runtime, or dependency manager.

---

# 3) Exact Outputs Under `.governance/`

Upon successful completion, the following outputs MUST exist under `.governance/`:

## 3.1 Core Governance Artifacts
- `.governance/governance-version.json` (copied from `../governance-version.json`)
- `.governance/project-profile.json` (per interrogation rules in `../bootstrap/project-interrogation.md`)
- `.governance/system-manifest.json` (per minimum requirements in `../bootstrap/BOOTSTRAP_PROMPT.md`)

## 3.2 Guardrails
- `.governance/guardrails/baseline-rules.yaml` (sourced from `../guardrails/baseline-rules.yaml`)
- `.governance/guardrails/validation-patterns.yaml` (sourced from `../guardrails/validation-patterns.yaml`)

## 3.3 Runtime Governance Artifacts (Vendored)
These MUST be copied into `.governance/` to ensure the governed repo is self-contained:
- `.governance/capability-registry.md` (from `../agents/capability-registry.md`)
- `.governance/session-start.md` (from `../agents/session-start.md`)
- `.governance/evidence-spec.md` (from `../bootstrap/evidence-spec.md`)

## 3.4 Agent Runtime Instruction
- `.governance/agent-runtime.md` (must declare required lifecycle and enforcement expectations)

## 3.5 Evidence Store
- `.governance/evidence/` directory
- `.governance/evidence/evidence.jsonl` (recommended minimal append-only store)

## 3.6 Learning System
- `.governance/learning/incidents/`
- `.governance/learning/proposals/`
- `.governance/learning/README.md` (summarizes learning lifecycle)

## 3.7 Status Report
- `.governance/status.md` (must include explicit statement: "No application code was modified during bootstrap.")

---

# 4) Success Criteria

A `governance init` run is successful only when the "Final Success Criteria" in `../bootstrap/BOOTSTRAP_PROMPT.md` are satisfied.

This includes:
- required files exist
- evidence supports completion claims (LAW 3)
- guardrails and patterns are installed
- learning system is initialized
- status report exists and is complete

---

# 5) Forbidden Actions (Hard Constraints)

The invocation MUST NOT:
- modify application/product code
- add/remove/update dependencies
- run destructive commands
- mutate runtime infrastructure or deployments
- introduce stack assumptions

Additionally, the invocation MUST NOT generate or propose organizational governance outputs, including:
- risk registers or risk matrices
- audit programs, audit plans, or audit schedules
- enterprise AI policies or compliance programs

---

# Validation Check C (Required)

This contract MUST NOT violate the identity and non-goals in `../bootstrap/BOOTSTRAP_IDENTITY.md`.

PASS if:
- outputs are strictly limited to `.governance/` and runtime governance artifacts
- no organizational risk/compliance governance artifacts are in scope
- stop condition is preserved (incorrect interpretation triggers STOP)
