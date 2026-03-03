# Governance Runtime Model (Behavioral Execution)

## Purpose
This document defines **how an agent executes governance** in a governed repository at runtime.

This is a behavioral execution model (load order, decision flow, evidence flow, refusal paths). It is not implementation code.

## Authority and Version Linkage
- Governance version source of truth: `../governance-version.json`
- Governed project version record: `.governance/governance-version.json`

If there is any conflict, the authoritative governance documents remain the source of truth:
- Session initialization: `../agents/session-start.md`
- Agent lifecycle contract: `../agents/agent-behaviour.md`
- Permission model: `../agents/capability-registry.md`
- Evidence schema: `../bootstrap/evidence-spec.md` (vendored as `.governance/evidence-spec.md`)
- Guardrails: `../guardrails/baseline-rules.yaml` (vendored under `.governance/guardrails/`)
- Validation patterns: `../guardrails/validation-patterns.yaml` (vendored under `.governance/guardrails/`)

---

# 1) Runtime Session Start (Load Sequence)

## 1.1 Mandatory Load Order
At the start of every session, the agent MUST follow the initialization sequence defined in `../agents/session-start.md`.

Runtime load order (normative):
1) Detect governance presence (`.governance/` directory)
2) Load governance version
   - In governed repo: `.governance/governance-version.json`
   - Otherwise: reference `../governance-version.json` (bootstrap context)
3) Read constitution laws (vendored equivalent if present)
4) Load capability registry `.governance/capability-registry.md` (governed projects)
5) Load project governance artifacts
   - `.governance/status.md` (if present)
   - `.governance/project-profile.json` and `.governance/system-manifest.json` (if present)
6) Load guardrails
   - `.governance/guardrails/*` when present; otherwise use bootstrap defaults as reference
7) Confirm readiness before planning
   - run minimum doctor checks required for the task
   - record evidence per `.governance/evidence-spec.md`

## 1.2 Governance Missing / Outdated
Behavior MUST follow `../agents/session-start.md`:
- If governance is missing: suggest running the bootstrap protocol (`../bootstrap/BOOTSTRAP_PROMPT.md`). If user declines, proceed only with explicit constraints and reduced claims (no completion without evidence).
- If governance is outdated: notify; do not auto-upgrade; offer a plan/proposal for human-approved upgrade.

---

# 2) Lifecycle Enforcement (Task Execution Loop)

## 2.1 Required Lifecycle
All task execution MUST follow `../agents/agent-behaviour.md` lifecycle:

Interrogate → Validate → Plan → Execute → Verify → Learn

## 2.2 Lifecycle Gate Conditions
Each step has minimum gates. Failing a gate yields either refusal/stop or an explicit “blocked” state with evidence.

### Interrogate (LAW 1)
Gate: repo reality is established for the task scope.
- Inputs: relevant project files, `.governance/project-profile.json`, `.governance/system-manifest.json`
- Output: clarified scope + identified unknowns

### Validate (Doctor Checks)
Gate: readiness is established using validation patterns.
- Inputs: `.governance/guardrails/validation-patterns.yaml`, task intent, environment signals
- Output: evidence-backed readiness or explicit blockers

### Plan (CHG-001)
Gate: intent + expected impact + evidence plan are stated.
- Inputs: guardrails + capability registry
- Output: a verifiable step plan including which evidence will support completion

### Execute (SAF-002, CHG-002)
Gate: change is permitted and bounded.
- Inputs: permission model + guardrails
- Output: smallest visible diff consistent with plan

### Verify (VER-001)
Gate: verification runs or explicit inability is recorded.
- Inputs: system manifest verification hooks and validation patterns
- Output: evidence supporting completion claims or “not fully verified” state

### Learn (LAW 6)
Gate: recurring failures generate incidents/proposals without auto-mutation.
- Inputs: `.governance/learning/*` and learning lifecycle rules
- Output: incident record and/or proposal requesting human approval

---

# 3) Guardrail Evaluation Flow

## 3.1 Inputs
- Guardrails: `.governance/guardrails/baseline-rules.yaml`
- Validation patterns: `.governance/guardrails/validation-patterns.yaml`
- Capability registry: `.governance/capability-registry.md`
- Constitution laws (vendored equivalent)

## 3.2 Evaluation Stages
The agent evaluates constraints in this order:
1) Constitution laws (highest precedence)
2) Guardrail rules (rule_id enforcement expectations)
3) Capability registry category (AI_CAN / AI_REQUIRES_CONFIRMATION / AI_CANNOT)
4) Local project constraints recorded in `.governance/project-profile.json` (protected paths, required confirmations)

## 3.3 Outcomes
- Allowed: proceed to next lifecycle step
- Requires confirmation: stop and request explicit human confirmation (must cite rule basis)
- Prohibited: refuse (must cite law/rule basis) and offer safe alternative
- Blocked by missing prerequisites: stop and report what is missing, with evidence

---

# 4) Evidence Recording Flow

## 4.1 Evidence Store
Evidence MUST be stored in files (not chat) per `.governance/evidence-spec.md` (vendored from `../bootstrap/evidence-spec.md`).

Minimum store:
- `.governance/evidence/evidence.jsonl` (append-only)

## 4.2 Evidence Events
Evidence should be recorded for:
- interrogation detections (paths, signals)
- environment discovery probes (command executable checks, config presence checks)
- changes applied (diff summary, impacted paths)
- verification runs (outputs, exit codes, summaries)
- refusals/blocks (what rule triggered, what evidence was missing)

## 4.3 Immutability
Evidence is append-only. Corrections are new entries that reference prior entries.

---

# 5) Refusal Decision Path

Refusals MUST follow `../agents/agent-behaviour.md` and `../agents/capability-registry.md`.

## 5.1 Trigger Conditions
Refuse or stop when:
- action violates constitution or guardrails
- action is destructive and lacks explicit confirmation (CHG-002 / SAF-001)
- completion is requested but evidence cannot be produced (VER-001; LAW 3)
- bootstrap rules would be violated (e.g., modifying application code during bootstrap)
- action would introduce stack assumptions (LAW 7)

## 5.2 Required Refusal Structure
Each refusal MUST:
- be explicit (what is refused)
- be grounded (cite constitution law and/or guardrail `rule_id`)
- be helpful (state what evidence/confirmation would allow proceeding; offer a safe alternative)

---

# Validation Check B (Required)

This runtime model MUST reference the following authoritative artifacts:
- `../agents/session-start.md`
- `../agents/agent-behaviour.md`
- `../agents/capability-registry.md`
- `../bootstrap/evidence-spec.md`

If any are missing, alignment FAILS.
