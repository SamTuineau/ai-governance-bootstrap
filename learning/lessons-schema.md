# Governance Evolution (Lessons Learned)

This document defines how governance evolves through controlled learning.

It operationalizes:
- **LAW 4 — Persistent Memory** and **LAW 6 — Controlled Evolution** from `../constitution/AI_ENGINEERING_CONSTITUTION.md`.
- The “Learn” step in the agent lifecycle from `../agents/agent-behaviour.md`.

## Lifecycle (Required)
**Incident → Analysis → Guardrail Proposal → Human Approval → Governance Update**

### 1) Incident
An incident is any failure, near-miss, or repeated friction that indicates missing or insufficient governance.

### 2) Analysis
Analyze cause, contributing factors, and what evidence supports the analysis.

### 3) Guardrail Proposal
Propose an enforceable change to guardrails and/or validation patterns.

### 4) Human Approval
Humans approve or reject proposals. Agents may draft proposals but must not auto-apply them.

### 5) Governance Update
After approval, update governance artifacts. Record the decision and link it to the originating incident.

Approved governance updates must follow the procedure defined in `./governance-update-protocol.md`. This protocol governs version increments, change recording, and propagation to future governed projects.

## Required Folder Structure (In Governed Projects)
Projects adopting this bootstrap must create:
```
.governance/learning/
	incidents/
	proposals/
```

## Templates

### Incident Record Template
Store under `.governance/learning/incidents/<YYYY-MM-DD>_<short-title>.md`.

```markdown
# Incident: <short title>

## Summary
- Date/time:
- Impact:
- Scope:
- Detected by:

## Evidence
- Links/paths to logs, command outputs, diffs, screenshots (if any):

## Timeline
- <time> - <event>

## Root Cause Analysis
- What happened:
- Why it happened:
- Contributing factors:

## Recovery / Mitigation
- Steps taken:

## Preventative Actions
- Proposed guardrail(s):
- Proposed validation(s):
- Owner (human):

## References
- Related guardrails:
- Related proposals:
```

### Guardrail Proposal Template
Store under `.governance/learning/proposals/<YYYY-MM-DD>_<short-title>.md`.

```markdown
# Guardrail Proposal: <short title>

## Motivation
- Linked incident(s):
- Problem statement:

## Proposed Change
- Target file(s):
- New/updated rule(s) or pattern(s):

## Enforcement Details
- What the agent must do:
- What is blocked/refused:
- Evidence required:

## Stack Neutrality Check
- Why this proposal does not assume a framework/tool:

## Risk Assessment
- False positives risk:
- False negatives risk:
- Backwards compatibility considerations:

## Approval
- Status: Draft | Approved | Rejected
- Approved by:
- Date:
```

## Controlled Self-Healing (Behavioral)
Agents may participate in self-healing only in a controlled way:

**Detect → Diagnose → Suggest → Prevent**
- **Detect:** Observe a failure signal with evidence.
- **Diagnose:** Identify likely cause(s) with evidence-backed reasoning.
- **Suggest:** Propose changes and/or a guardrail proposal.
- **Prevent:** After human approval, update governance artifacts so the failure becomes harder to repeat.

## Explicit Prohibition
Agents must **never** automatically mutate governance rules or validation patterns. They may draft proposals and request approval, but rule mutation is a human-controlled action.
