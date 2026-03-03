# Governance Update Protocol (After Approval)

This document defines the exact process for updating governance after a proposal is approved.

It extends the learning lifecycle in `./lessons-schema.md` and enforces:
- **LAW 2 — Observable Change**
- **LAW 4 — Persistent Memory**
- **LAW 6 — Controlled Evolution**

## Lifecycle (Required)
**Approved Proposal → Governance Repo Update → Version Increment → Change Log Entry → Future Bootstrap Adoption**

### Step 1 — Approved Proposal
Input: an approved proposal record in the governed project (see `./lessons-schema.md`).

Required properties of approval:
- explicit approval recorded (who/when)
- linked incident(s)
- defined change scope

### Step 2 — Governance Repo Update
Apply the approved change to this governance bootstrap repository.

Rules:
- updates must be visible as diffs
- no silent changes
- preserve stack neutrality
- do not change bootstrap phases (only extend references/requirements when needed)

### Step 3 — Version Increment
Update the root `../governance-version.json` using semantic versioning rules below.

### Step 4 — Change Log Entry
Record a change log entry by updating the **approved proposal document** to include:
- governance version applied
- date applied
- summary of changes
- links to modified files

This keeps the changelog co-located with the approval record (persistent memory) without requiring a specific tooling system.

### Step 5 — Future Bootstrap Adoption
Future governed projects adopt the updated governance through the normal bootstrap protocol. Agents must not auto-upgrade governance in existing projects; they may only notify about newer versions.

## Semantic Versioning Rules
Governance uses semantic versioning: `MAJOR.MINOR.PATCH`.

### PATCH (backwards compatible)
Increment PATCH for:
- guardrail additions (new rules that do not change existing semantics)
- validation pattern improvements (clarifications, additional optional guidance)
- documentation clarifications that do not change meanings

### MINOR (new capabilities, compatible)
Increment MINOR for:
- bootstrap enhancements that add new optional outputs or clarifications
- new governance layers that do not alter existing law meanings or lifecycle semantics

### MAJOR (breaking governance semantics)
Increment MAJOR for:
- constitution changes (law meanings, enforcement expectations)
- lifecycle changes (bootstrap phase definitions or required agent lifecycle changes)
- any change that invalidates prior governed project artifacts

## Prohibition: Silent Updates
Governance updates must never be applied silently.

Minimum observability requirements:
- intent + expected impact documented
- diffs visible
- version updated
- approval record updated with changelog section
