# Execution Layer — Governed Bootstrap Runner

This repository provides deterministic, stack-neutral bootstrap runners that initialize governed project artifacts under `.governance/`.

Non-negotiables:
- Only `.governance/` is written/modified by these runners.
- Default behavior is SAFE: refuse to run if `.governance/` already exists.
- Phase order is fixed (0 → 7) and evidence is recorded to `.governance/evidence/evidence.jsonl`.

## Runners

- PowerShell (Windows-first): `tools/governance-init.ps1`
- POSIX shell (macOS/Linux): `tools/governance-init.sh`

Both implement the same phase sequence described in `runtime/bootstrap-execution-spec.md`.

## Usage

### PowerShell

- Dry-run (no writes):

  `powershell -NoProfile -ExecutionPolicy Bypass -File tools/governance-init.ps1 -TargetPath . -DryRun`

- Write mode (SAFE default):

  `powershell -NoProfile -ExecutionPolicy Bypass -File tools/governance-init.ps1 -TargetPath .`

- Force overwrite governed artifacts (ONLY `.governance/`):

  `powershell -NoProfile -ExecutionPolicy Bypass -File tools/governance-init.ps1 -TargetPath . -Force`

### Shell

- Dry-run (no writes):

  `sh tools/governance-init.sh --target . --dry-run`

- Write mode (SAFE default):

  `sh tools/governance-init.sh --target .`

- Force overwrite governed artifacts (ONLY `.governance/`):

  `sh tools/governance-init.sh --target . --force`

## Outputs (created under `.governance/`)

- `project-profile.json` (Phase 1)
- `evidence/evidence.jsonl` (Phase 2)
- `governance-version.json` and `system-manifest.json` (Phase 3)
- `guardrails/baseline-rules.yaml` and `guardrails/validation-patterns.yaml` (Phase 4)
- `capability-registry.md`, `session-start.md`, `evidence-spec.md`, `agent-runtime.md` (Phase 5)
- `learning/incidents/`, `learning/proposals/`, `learning/README.md` (Phase 6)
- `status.md` (Phase 7)

## VS Code “One Button”

Tasks are provided in `.vscode/tasks.json`:
- `Governance: Init (PowerShell)`
- `Governance: Init Dry Run (PowerShell)`
- `Governance: Init (Shell)`
- `Governance: Init Dry Run (Shell)`

Run via: Terminal → Run Task…

## Determinism and Safety

- Determinism: fixed phase ordering; evidence entries include phase/action/timestamp and are written as JSON Lines.
- Safety: refuses when `.governance/` already exists unless `--force` / `-Force` is provided.
- Scope: scripts copy vendored governance artifacts from this repo into `.governance/`; they do not install dependencies or run build/test commands.

## Portability Notes

- On Windows, the Shell runner/tasks require a POSIX shell (e.g., WSL with a distro installed, or Git Bash). If unavailable, use the PowerShell runner.
