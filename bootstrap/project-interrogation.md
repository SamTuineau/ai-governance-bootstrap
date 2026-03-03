# Project Interrogation (Reality Discovery)

This document defines how agents discover project reality in a deterministic, stack-neutral way.

Interrogation exists to satisfy **LAW 1 — Reality Before Action** in `../constitution/AI_ENGINEERING_CONSTITUTION.md`.

## Operating Rules
- Prefer automatic detection from repository signals.
- Ask humans only when required to unblock governance (not to guess a stack).
- Capture findings as **persistent memory** in `.governance/project-profile.json`.

## Automatic Detection Rules
The agent must attempt the following detections (best-effort) using read-only inspection.

### Languages
Detect languages by combining:
- File extensions (e.g., `*.py`, `*.js`, `*.ts`, `*.java`, `*.cs`, `*.go`, `*.rs`, `*.rb`, `*.php`, `*.scala`, `*.kt`, `*.swift`, `*.m`, `*.cpp`, `*.c`, `*.h`).
- Language-specific “root signals” (e.g., presence of a canonical project file or manifest).
- Shebangs in executable scripts (first line `#!...`).

**Rule:** if extension-based detection conflicts with root signals, root signals win and extension-based detection becomes “secondary”.

### Repository Signals
Collect and record:
- Top-level docs: `README*`, `CONTRIBUTING*`, `SECURITY*`, `CODEOWNERS`, `LICENSE*`.
- Governance or policy hints: `docs/`, `adr/` or `decisions/`, `.editorconfig`.
- Monorepo indicators: multiple independent manifests in subfolders.

### Dependency Managers
Detect dependency managers by the presence of manifest/lock files. Examples of *signals* (not requirements):
- Manifest files (package manifests, module manifests, project definitions).
- Lockfiles or resolved dependency snapshots.

**Rule:** record both the manifest location and the lockfile location(s), if any.

### CI Presence
Detect CI by locating pipeline definitions, for example:
- `.github/workflows/`
- files containing “pipeline” definitions at repo root
- any folder or file explicitly describing automated checks

Record:
- provider-agnostic presence (`true/false`)
- paths to CI definitions

### Containers
Detect containerization signals (without assuming containers are required):
- `Dockerfile*`
- container orchestration definitions
- dev environment descriptors (e.g., dev container configs)

Record paths and whether they appear actively referenced by docs or CI.

### Runtime Clues
Detect runtime/version hints:
- version pinning files (e.g., toolchain version files)
- `.env*` templates, example configs, or required secrets references
- scripts and “make-like” automation in docs

Record:
- discovered runtime hints
- whether values are present or only referenced

## Human Questions (Only When Required)
The agent may ask humans questions only when:
- a critical governance decision cannot be derived from repo state, and
- not asking would risk unsafe actions or incomplete verification.

When asking, keep questions minimal and structured:
- ask at most 3 questions
- include why each is required
- offer “unknown” as an allowed answer

Examples of valid questions:
- “Which command (if any) is considered the project’s canonical ‘verification’ command?”
- “Are there environment variables required to run validations locally?”

Examples of invalid questions:
- “What framework do you want?”
- “Should we rewrite the project?”

## Example Interrogation Dialogue
**Agent:** I found multiple manifests under `/services/` and `/libs/`, indicating a multi-package repository. I will create `.governance/project-profile.json` capturing these paths. Are there any directories that must never be modified by automation (e.g., generated artifacts or vendor folders)?

**Human:** Do not modify `/vendor/` and `/generated/`.

**Agent:** Acknowledged. I will record those directories as protected paths and will require explicit confirmation before any operation that touches them.

## Output Schema — `.governance/project-profile.json`
This file is the canonical record of interrogation results.

### Schema (conceptual)
Required top-level fields:
- `schema_version` (string)
- `generated_at` (ISO-8601 string)
- `repo_root` (string)
- `signals` (object)
- `detections` (object)
- `constraints` (object)
- `unknowns` (array of strings)
- `evidence` (array of objects)

Recommended structure:
```json
{
	"schema_version": "1.0",
	"generated_at": "2026-02-26T00:00:00Z",
	"repo_root": ".",
	"signals": {
		"readme_paths": ["README.md"],
		"policy_paths": [],
		"monorepo": false
	},
	"detections": {
		"languages": [
			{
				"name": "<detected-language>",
				"confidence": "high",
				"evidence_paths": ["<path1>", "<path2>"]
			}
		],
		"dependency_managers": [
			{
				"name": "<manager>",
				"manifest_paths": ["<manifest>"] ,
				"lock_paths": ["<lock>"]
			}
		],
		"ci": {
			"present": false,
			"definition_paths": []
		},
		"containers": {
			"present": false,
			"definition_paths": []
		},
		"runtime_clues": {
			"version_pin_paths": [],
			"env_template_paths": [],
			"automation_paths": []
		}
	},
	"constraints": {
		"protected_paths": [],
		"required_confirmations": [],
		"notes": []
	},
	"unknowns": [],
	"evidence": [
		{
			"type": "file_presence",
			"path": "README.md",
			"observed": true,
			"observed_at": "2026-02-26T00:00:00Z"
		}
	]
}
```

### Evidence Rules
- Evidence entries must be falsifiable (someone can re-check them).
- Prefer “observed paths” over narrative.
- Link evidence to the governing laws (especially LAW 1 and LAW 3).
