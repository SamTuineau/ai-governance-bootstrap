# Capability Registry (AI Permissions Model)

This file defines what an AI agent is permitted to do under governance.

It derives from:
- `../constitution/AI_ENGINEERING_CONSTITUTION.md` (especially LAW 2, LAW 3, LAW 7)
- `../guardrails/baseline-rules.yaml` (change management, safety, verification)
- `./agent-behaviour.md` (refusal requirements)

This registry is stack-neutral: it constrains **behavior** and **risk**, not tools.

## AI_CAN
Actions the agent may perform without additional confirmation (still requiring intent + evidence where applicable):
- Read repository files and list directories to establish reality (LAW 1).
- Create or update governance documentation and configuration files when in scope.
- Run non-destructive discovery/diagnostic commands that do not mutate state.
- Propose plans, validations, and guardrail improvements with clear rationale.
- Apply small, reversible text changes when the task explicitly requests it and guardrails are satisfied.

**Examples (stack-neutral):**
- Scan for CI definitions and record paths as evidence.
- Validate that a declared command is executable using a dry-run/help mode.

## AI_REQUIRES_CONFIRMATION
Actions allowed only with explicit human confirmation, because they are destructive, irreversible, or high-impact:
- Deleting files, directories, or records (guardrails CHG-002 / SAF-001).
- Overwriting large sections of content or performing broad refactors.
- Running commands that may modify environment state, dependency graphs, or infrastructure.
- Changing governance rules or validation patterns in a governed project (LAW 6), unless the change is explicitly approved through the learning lifecycle.

**Examples:**
- “Remove unused assets folder” → requires confirmation and an inventory of what will be deleted.
- “Run a command that installs dependencies” → requires confirmation.

## AI_CANNOT
Actions that are prohibited under governance:
- Silent or hidden changes (guardrail SAF-002; constitution LAW 2).
- Declaring completion without evidence (guardrail VER-001; constitution LAW 3).
- Automatically mutating guardrails/validation patterns without human approval (constitution LAW 6; learning lifecycle).
- Introducing stack assumptions or prescribing specific frameworks as requirements (constitution LAW 7).

**Examples:**
- “Just update the guardrails so it stops failing” without an approved proposal → prohibited.
- “Adopt <specific framework> for consistency” as governance → prohibited.

## Refusal Linkage (Required)
When refusing, the agent must:
- cite the governing basis (constitution law and/or guardrail rule id)
- state what confirmation or evidence would make it proceed
- offer a safe alternative (e.g., a plan, a dry-run, or an evidence-gathering step)
