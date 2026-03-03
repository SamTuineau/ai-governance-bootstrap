# Capability Expansion Map (Governed Boundaries)

## Purpose
This document maps the current governance system coverage against broader one-button project goals.

It defines **governed extension boundaries** only. It does not implement infrastructure tooling.

## Authority and Version Linkage
- Governance version source of truth: `../governance-version.json`
- Governed project version record: `.governance/governance-version.json`

All future capability expansions MUST operate through the governed lifecycle and constraints:
- Lifecycle: Interrogate → Validate → Plan → Execute → Verify → Learn (`../agents/agent-behaviour.md`)
- Guardrails: `.governance/guardrails/*` (vendored from `../guardrails/*`)
- Evidence: `.governance/evidence/*` per `.governance/evidence-spec.md`
- Controlled evolution: proposals + human approval (`../learning/lessons-schema.md`, `../learning/governance-update-protocol.md`)

## Classification Legend
- **SUPPORTED BY GOVERNANCE**: governance artifacts already define behavioral constraints + evidence/verification patterns for the capability class.
- **ALLOWED BUT NOT IMPLEMENTED**: permitted as engineering work, but this repository does not provide the runtime execution/automation layer yet.
- **OUT OF SCOPE**: prohibited by bootstrap identity/scope or requires organizational governance beyond repo execution governance.

---

# Capability Areas

## 1) Repo Setup (Project Initialization)
- Classification: **ALLOWED BUT NOT IMPLEMENTED**
- Governance support present:
  - Bootstrap installs `.governance/` deterministically (`../bootstrap/BOOTSTRAP_PROMPT.md`).
  - Stack-neutral repo interrogation + manifest creation define how to detect what already exists.
- Notes:
  - Creating application scaffolds, dependencies, or framework setups is explicitly outside bootstrap scope.

## 2) CI/CD
- Classification: **SUPPORTED BY GOVERNANCE** (detection + verification semantics), **ALLOWED BUT NOT IMPLEMENTED** (execution)
- Governance support present:
  - Interrogation requires detecting CI definitions and recording paths (`../bootstrap/project-interrogation.md`).
  - Validation patterns include command executability checks (PAT-005).
  - Guardrails enforce intent, non-destructive behavior, and evidence-based completion.
- Not implemented here:
  - generation or modification of CI pipelines is not provided as a one-button capability.

## 3) Testing Lifecycle
- Classification: **SUPPORTED BY GOVERNANCE** (verification rules), **ALLOWED BUT NOT IMPLEMENTED** (test orchestration)
- Governance support present:
  - LAW 3 + VER-001 require evidence-backed verification.
  - Validation patterns provide reusable patterns for command exec, config validity, endpoint probes.
- Not implemented here:
  - test discovery, standardization, and cross-stack test execution tooling.

## 4) Security Baseline
- Classification: **ALLOWED BUT NOT IMPLEMENTED**
- Governance support present:
  - Change management and safety guardrails reduce risky automation.
  - Evidence requirements can capture security checks if a project already defines them.
- Not implemented here:
  - no universal security control catalog, scanning integration, secret management tooling, or baseline hardening actions.

## 5) Observability
- Classification: **SUPPORTED BY GOVERNANCE** (governance observability), **ALLOWED BUT NOT IMPLEMENTED** (system observability)
- Governance support present:
  - Evidence store + status report provide an audit trail for governance actions.
- Not implemented here:
  - application telemetry standards (metrics/logging/tracing) or instrumentation.

## 6) Backups / Recovery
- Classification: **ALLOWED BUT NOT IMPLEMENTED**
- Governance support present:
  - Guardrails require confirmation for destructive actions and discourage irreversible operations.
- Not implemented here:
  - backup automation and restore validation.

## 7) Drift Detection
- Classification: **SUPPORTED BY GOVERNANCE** (version drift), **ALLOWED BUT NOT IMPLEMENTED** (broader drift)
- Governance support present:
  - session-start includes governance version awareness and “do not auto-upgrade” behavior.
  - evidence can record detected drift signals.
- Not implemented here:
  - continuous checks for configuration drift, dependency drift, infra drift.

---

# Governance-First Constraint (Non-Bypass Rule)

No capability expansion may bypass the governed execution lifecycle.

Minimum governance gates for any future execution-layer capability:
- **Interrogate:** detect existing state from repo signals; do not assume.
- **Validate:** run stack-neutral doctor checks and record evidence.
- **Plan:** state intent, impact, and evidence plan (CHG-001).
- **Execute:** apply minimal visible diffs only; confirmation for destructive actions (CHG-002/SAF-001).
- **Verify:** do not claim completion without evidence (VER-001).
- **Learn:** convert recurring failures into proposals; no auto-mutation of governance rules (LAW 6).

---

# Validation Check E (Required)

PASS if this document:
- does not authorize any direct state mutation outside the lifecycle steps
- does not define any capability that operates around guardrails/evidence/refusal rules
- keeps infrastructure work unimplemented (execution layer is future work)
