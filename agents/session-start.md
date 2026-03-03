# Agent Session Start Contract

This contract defines the mandatory initialization sequence at the start of every agent session.

It operationalizes:
- **LAW 1 — Reality Before Action** (interrogate first)
- **LAW 3 — Evidence-Based Completion** (evidence-aware verification)
- **LAW 6 — Controlled Evolution** (no auto-upgrades)

## Mandatory Initialization Sequence
Agents must perform these steps in order before planning or executing work:

1) **Detect governance presence**
   - If project contains `.governance/`, treat it as a governed project.
   - If absent, treat it as not yet governed.

2) **Load governance version**
   - In bootstrap repo: read `../governance-version.json`.
   - In governed project: read `.governance/governance-version.json` (if present).

3) **Read constitution**
   - Load the governing laws from `../constitution/AI_ENGINEERING_CONSTITUTION.md` (or the project’s vendored equivalent).

4) **Load capability registry**
   - In governed projects, read `.governance/capability-registry.md`.

5) **Read project governance artifacts (`.governance/*`)**
   - Prefer `.governance/status.md`, `.governance/project-profile.json`, `.governance/system-manifest.json`.

6) **Load guardrails**
   - Load `.governance/guardrails/*` when present; otherwise, use bootstrap defaults as reference.

7) **Confirm readiness before planning**
   - Run the minimum doctor checks required for the task.
   - Record evidence according to `.governance/evidence-spec.md`.

## Fallback Behavior

### Governance Missing
If governance is missing (no `.governance/` directory):
- Do not proceed with changes as if governance exists.
- Suggest running the bootstrap protocol defined in `../bootstrap/BOOTSTRAP_PROMPT.md`.
- If the user declines, proceed only with explicit constraints and reduced claims (no “complete” without evidence).

### Governance Outdated
If a newer governance version exists than the one recorded in `.governance/governance-version.json`:
- Notify clearly that governance is outdated.
- Do not auto-upgrade.
- Offer to generate a proposal/plan for a human-approved upgrade.
