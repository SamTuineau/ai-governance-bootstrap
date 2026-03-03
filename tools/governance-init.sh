#!/usr/bin/env sh
set -eu

# governance-init.sh — deterministic governance bootstrap runner
# Stack-neutral: does not require Node/Python/etc; uses POSIX shell + standard utilities.

TARGET="."
DRY_RUN=0
FORCE=0

usage() {
  cat <<'USAGE'
Usage: tools/governance-init.sh [--target PATH] [--dry-run] [--force]

Defaults:
  --target   . (current directory)

Modes:
  --dry-run  Print planned operations and checks; no writes
  --force    Allow running when .governance/ already exists (overwrites governance artifacts only)
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --target)
      TARGET="$2"; shift 2 ;;
    --dry-run)
      DRY_RUN=1; shift ;;
    --force)
      FORCE=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

info() { printf '%s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# Resolve absolute paths (portable-ish)
if command -v realpath >/dev/null 2>&1; then
  TARGET_FULL="$(realpath "$TARGET")"
else
  # fallback: cd + pwd
  TARGET_FULL="$(cd "$TARGET" 2>/dev/null && pwd)" || fail "Target path not found: $TARGET"
fi

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BOOTSTRAP_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

GOV_DIR="$TARGET_FULL/.governance"
EVID_DIR="$GOV_DIR/evidence"
EVID_FILE="$EVID_DIR/evidence.jsonl"

if [ -d "$GOV_DIR" ] && [ "$FORCE" -ne 1 ]; then
  fail "SAFE MODE: Target already contains .governance/. Refusing. Re-run with --force to overwrite governed artifacts."
fi

iso_ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

session_id() {
  stamp="$(date -u '+%Y%m%dT%H%M%SZ')"
  # cksum is POSIX; use it to derive a stable short id for this invocation timestamp
  sum="$(printf '%s' "$TARGET_FULL|$stamp" | cksum | awk '{print $1}')"
  printf '%s-%s' "$stamp" "$sum"
}

SID="$(session_id)"

json_escape() {
  # Escapes a string for JSON
  # shellcheck disable=SC1003
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e ':a;N;$!ba;s/\n/\\n/g'
}

json_array() {
  # arguments: list of strings
  out="["
  first=1
  for v in "$@"; do
    if [ "$first" -eq 1 ]; then first=0; else out="$out,"; fi
    out="$out\"$(json_escape "$v")\""
  done
  out="$out]"
  printf '%s' "$out"
}

append_evidence_line() {
  phase="$1"; action="$2"; input="$3"; result="$4"; confidence="$5"; source="$6"
  line="{\"timestamp\":\"$(iso_ts)\",\"phase\":\"$(json_escape "$phase")\",\"action\":\"$(json_escape "$action")\",\"input\":\"$(json_escape "$input")\",\"result\":\"$(json_escape "$result")\",\"confidence\":\"$(json_escape "$confidence")\",\"source\":\"$(json_escape "$source")\"}"
  if [ "$DRY_RUN" -eq 1 ]; then
    info "[DRY-RUN] evidence: $line"
    return
  fi
  printf '%s\n' "$line" >> "$EVID_FILE"
}

mkdir_p() {
  if [ "$DRY_RUN" -eq 1 ]; then
    info "[DRY-RUN] mkdir -p $1"
    return
  fi
  mkdir -p "$1"
}

write_file() {
  path="$1"
  if [ "$DRY_RUN" -eq 1 ]; then
    info "[DRY-RUN] write $path"
    # consume stdin to avoid broken pipe in pipelines
    cat >/dev/null || true
    return
  fi
  mkdir -p "$(dirname "$path")"
  # content is on stdin
  cat > "$path"
}

copy_file() {
  src="$1"; dst="$2"
  if [ "$DRY_RUN" -eq 1 ]; then
    info "[DRY-RUN] copy $src -> $dst"
    return
  fi
  mkdir -p "$(dirname "$dst")"
  cp -f "$src" "$dst"
}

# Validate authoritative sources exist (execution-layer dependency only)
req_files="
$BOOTSTRAP_ROOT/bootstrap/BOOTSTRAP_PROMPT.md
$BOOTSTRAP_ROOT/bootstrap/BOOTSTRAP_IDENTITY.md
$BOOTSTRAP_ROOT/runtime/bootstrap-execution-spec.md
$BOOTSTRAP_ROOT/runtime/project-bootstrap-contract.md
$BOOTSTRAP_ROOT/agents/session-start.md
$BOOTSTRAP_ROOT/agents/capability-registry.md
$BOOTSTRAP_ROOT/bootstrap/evidence-spec.md
$BOOTSTRAP_ROOT/guardrails/baseline-rules.yaml
$BOOTSTRAP_ROOT/guardrails/validation-patterns.yaml
$BOOTSTRAP_ROOT/governance-version.json
"
for f in $req_files; do
  [ -f "$f" ] || fail "Missing required bootstrap source file: $f"
done

info "Governance Init (Shell)"
info "Target: $TARGET_FULL"
info "Session: $SID"
if [ "$DRY_RUN" -eq 1 ]; then info "Mode: DRY-RUN"; else info "Mode: WRITE"; fi
if [ "$FORCE" -eq 1 ]; then info "Safety: FORCE"; else info "Safety: SAFE"; fi

# Buffer evidence until Phase 2 creates the evidence store
EVID_BUF=""
add_buf_evidence() {
  phase="$1"; action="$2"; input="$3"; result="$4"; confidence="$5"; source="$6"
  line="{\"timestamp\":\"$(iso_ts)\",\"phase\":\"$(json_escape "$phase")\",\"action\":\"$(json_escape "$action")\",\"input\":\"$(json_escape "$input")\",\"result\":\"$(json_escape "$result")\",\"confidence\":\"$(json_escape "$confidence")\",\"source\":\"$(json_escape "$source")\"}"
  EVID_BUF="$EVID_BUF$line\n"
}

CREATED_LIST=""
track_created() {
  CREATED_LIST="$CREATED_LIST$1\n"
}

# -------------------------
# Phase 0 — Invocation Rules
# -------------------------
add_buf_evidence "phase-0" "bootstrap_invocation" "target=$TARGET_FULL dry_run=$DRY_RUN force=$FORCE" "session_id=$SID scope=governance-artifacts-only" "high" "execution_layer"

# -------------------------
# Phase 1 — Project Interrogation
# -------------------------
# Find signals (exclude .governance/.git and common build/vendor dirs)
find_files() {
  # prints absolute paths
  find "$TARGET_FULL" -type f \
    ! -path '*/.governance/*' \
    ! -path '*/.git/*' \
    ! -path '*/node_modules/*' \
    ! -path '*/dist/*' \
    ! -path '*/build/*' \
    ! -path '*/out/*' \
    ! -path '*/.venv/*' \
    ! -path '*/venv/*' 2>/dev/null
}

relpath() {
  # best-effort relative path
  case "$1" in
    "$TARGET_FULL"/*) printf '%s' "${1#"$TARGET_FULL"/}" ;;
    *) printf '%s' "$1" ;;
  esac
}

READMES="$(find "$TARGET_FULL" -maxdepth 1 -type f -name 'README*' 2>/dev/null | sort || true)"
POLICY="$(find "$TARGET_FULL" -maxdepth 1 -type f \( -name 'SECURITY*' -o -name 'CONTRIBUTING*' -o -name 'CODEOWNERS' -o -name 'LICENSE*' -o -name '.editorconfig' \) 2>/dev/null | sort || true)"

# Detections
CI_DEFS=""
[ -d "$TARGET_FULL/.github/workflows" ] && CI_DEFS="${CI_DEFS}$(relpath "$TARGET_FULL/.github/workflows")\n"
[ -f "$TARGET_FULL/azure-pipelines.yml" ] && CI_DEFS="${CI_DEFS}azure-pipelines.yml\n"
[ -f "$TARGET_FULL/.gitlab-ci.yml" ] && CI_DEFS="${CI_DEFS}.gitlab-ci.yml\n"
[ -f "$TARGET_FULL/Jenkinsfile" ] && CI_DEFS="${CI_DEFS}Jenkinsfile\n"

CONTAINER_DEFS=""
for df in $(find_files | sed -n 's#.*/\(Dockerfile[^/]*\)$#\1#p' | sort -u || true); do
  CONTAINER_DEFS="${CONTAINER_DEFS}${df}\n"
done
[ -f "$TARGET_FULL/docker-compose.yml" ] && CONTAINER_DEFS="${CONTAINER_DEFS}docker-compose.yml\n"
[ -f "$TARGET_FULL/docker-compose.yaml" ] && CONTAINER_DEFS="${CONTAINER_DEFS}docker-compose.yaml\n"
[ -d "$TARGET_FULL/.devcontainer" ] && CONTAINER_DEFS="${CONTAINER_DEFS}.devcontainer\n"

# Dependency managers (stack-neutral detection)
DM_NODE_MAN="$(find_files | sed -n 's#.*/package\.json$#package.json#p' | wc -l | awk '{print $1}')"
DM_PY_MAN="$(find_files | sed -n 's#.*/\(pyproject\.toml\|requirements\.txt\|Pipfile\)$#\1#p' | wc -l | awk '{print $1}')"
DM_GO_MAN="$(find_files | sed -n 's#.*/go\.mod$#go.mod#p' | wc -l | awk '{print $1}')"
DM_RS_MAN="$(find_files | sed -n 's#.*/Cargo\.toml$#Cargo.toml#p' | wc -l | awk '{print $1}')"

LANGS=""
[ "$DM_NODE_MAN" -gt 0 ] && LANGS="${LANGS}JavaScript/TypeScript\n"
[ "$DM_PY_MAN" -gt 0 ] && LANGS="${LANGS}Python\n"
[ "$DM_GO_MAN" -gt 0 ] && LANGS="${LANGS}Go\n"
[ "$DM_RS_MAN" -gt 0 ] && LANGS="${LANGS}Rust\n"
LANGS_SORTED="$(printf '%s' "$LANGS" | sed '/^$/d' | sort -u || true)"

# Unknowns
UNKNOWNS="CI presence not detected (may be absent or non-standard).\nCanonical verification command unknown unless declared in repo signals.\n"

# Build minimal project-profile.json per bootstrap/project-interrogation.md required fields
PROFILE_PATH="$GOV_DIR/project-profile.json"

mkdir_p "$GOV_DIR"
# Write profile
{
  ts="$(iso_ts)"
  readme_json="[]"
  policy_json="[]"

  if [ -n "$READMES" ]; then
    set --
    for p in $READMES; do set -- "$@" "$(relpath "$p")"; done
    readme_json="$(json_array "$@")"
  fi
  if [ -n "$POLICY" ]; then
    set --
    for p in $POLICY; do set -- "$@" "$(relpath "$p")"; done
    policy_json="$(json_array "$@")"
  fi

  langs_json="[]"
  if [ -n "$LANGS_SORTED" ]; then
    # represent each as an object with minimal evidence
    objs=""
    first=1
    for l in $LANGS_SORTED; do
      if [ "$first" -eq 1 ]; then first=0; else objs="$objs,"; fi
      objs="$objs{\"name\":\"$(json_escape "$l")\",\"confidence\":\"high\",\"evidence_paths\":[]}" 
    done
    langs_json="[$objs]"
  fi

  ci_present="false"; ci_paths="[]"
  if [ -n "$CI_DEFS" ]; then
    ci_present="true"
    set --
    for p in $(printf '%s' "$CI_DEFS" | sed '/^$/d' | sort -u); do set -- "$@" "$p"; done
    ci_paths="$(json_array "$@")"
  fi

  cont_present="false"; cont_paths="[]"
  if [ -n "$CONTAINER_DEFS" ]; then
    cont_present="true"
    set --
    for p in $(printf '%s' "$CONTAINER_DEFS" | sed '/^$/d' | sort -u); do set -- "$@" "$p"; done
    cont_paths="$(json_array "$@")"
  fi

  # dependency_managers objects are intentionally minimal here (counts-only in shell runner)
  dep_objs=""
  dep_first=1
  if [ "$DM_NODE_MAN" -gt 0 ]; then
    [ "$dep_first" -eq 1 ] && dep_first=0 || dep_objs="$dep_objs,"
    dep_objs="$dep_objs{\"name\":\"node\",\"manifest_paths\":[],\"lock_paths\":[]}" 
  fi
  if [ "$DM_PY_MAN" -gt 0 ]; then
    [ "$dep_first" -eq 1 ] && dep_first=0 || dep_objs="$dep_objs,"
    dep_objs="$dep_objs{\"name\":\"python\",\"manifest_paths\":[],\"lock_paths\":[]}" 
  fi
  if [ "$DM_GO_MAN" -gt 0 ]; then
    [ "$dep_first" -eq 1 ] && dep_first=0 || dep_objs="$dep_objs,"
    dep_objs="$dep_objs{\"name\":\"go\",\"manifest_paths\":[],\"lock_paths\":[]}" 
  fi
  if [ "$DM_RS_MAN" -gt 0 ]; then
    [ "$dep_first" -eq 1 ] && dep_first=0 || dep_objs="$dep_objs,"
    dep_objs="$dep_objs{\"name\":\"cargo\",\"manifest_paths\":[],\"lock_paths\":[]}" 
  fi
  dep_json="[$dep_objs]"

  unknowns_json="[]"
  set --
  printf '%s' "$UNKNOWNS" | sed '/^$/d' | while IFS= read -r u; do
    set -- "$@" "$u"
  done

  # Note: shell POSIX portability makes array building in subshell complex; keep unknowns minimal
  unknowns_json='["CI presence not detected (may be absent or non-standard).","Canonical verification command unknown unless declared in repo signals."]'

  cat <<JSON
{
  "schema_version": "1.0",
  "generated_at": "$ts",
  "repo_root": ".",
  "signals": {
    "readme_paths": $readme_json,
    "policy_paths": $policy_json,
    "monorepo": false
  },
  "detections": {
    "languages": $langs_json,
    "dependency_managers": $dep_json,
    "ci": {"present": $ci_present, "definition_paths": $ci_paths},
    "containers": {"present": $cont_present, "definition_paths": $cont_paths},
    "runtime_clues": {"version_pin_paths": [], "env_template_paths": [], "automation_paths": []}
  },
  "constraints": {"protected_paths": [], "required_confirmations": [], "notes": []},
  "unknowns": $unknowns_json,
  "evidence": []
}
JSON
} | write_file "$PROFILE_PATH"
track_created "project-profile.json"

add_buf_evidence "phase-1" "project_interrogation" "file_scan=best_effort" "profile_written=.governance/project-profile.json" "high" "repo_scan"

# -------------------------
# Phase 2 — Environment Discovery (create evidence store)
# -------------------------
mkdir_p "$EVID_DIR"
if [ "$DRY_RUN" -eq 1 ]; then
  info "[DRY-RUN] create $EVID_FILE"
else
  : > "$EVID_FILE"
  track_created "evidence/evidence.jsonl"
  # flush buffered evidence
  printf '%b' "$EVID_BUF" >> "$EVID_FILE"
fi
append_evidence_line "phase-2" "environment_discovery" "shell=posix" "evidence_store=.governance/evidence/evidence.jsonl" "high" "execution_layer"

# -------------------------
# Phase 3 — System Manifest Creation
# -------------------------
copy_file "$BOOTSTRAP_ROOT/governance-version.json" "$GOV_DIR/governance-version.json"
track_created "governance-version.json"

# Extract governance_name and version without external JSON tooling
GOV_NAME="$(sed -n 's/^[[:space:]]*"governance_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$BOOTSTRAP_ROOT/governance-version.json" | head -n 1 || true)"
GOV_VER="$(sed -n 's/^[[:space:]]*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$BOOTSTRAP_ROOT/governance-version.json" | head -n 1 || true)"
[ -n "$GOV_NAME" ] || GOV_NAME="AI Governance Bootstrap"
[ -n "$GOV_VER" ] || GOV_VER="unknown"

# Minimal system-manifest.json with required minimums
MANIFEST_PATH="$GOV_DIR/system-manifest.json"
{
  ts="$(iso_ts)"
  proj_name="$(basename "$TARGET_FULL")"

  det_langs_json="[]"
  if [ -n "$LANGS_SORTED" ]; then
    set --
    for l in $LANGS_SORTED; do set -- "$@" "$l"; done
    det_langs_json="$(json_array "$@")"
  fi

  det_deps=""
  [ "$DM_NODE_MAN" -gt 0 ] && det_deps="${det_deps}node\n"
  [ "$DM_PY_MAN" -gt 0 ] && det_deps="${det_deps}python\n"
  [ "$DM_GO_MAN" -gt 0 ] && det_deps="${det_deps}go\n"
  [ "$DM_RS_MAN" -gt 0 ] && det_deps="${det_deps}cargo\n"
  det_deps_sorted="$(printf '%s' "$det_deps" | sed '/^$/d' | sort -u || true)"
  det_deps_json="[]"
  if [ -n "$det_deps_sorted" ]; then
    set --
    for d in $det_deps_sorted; do set -- "$@" "$d"; done
    det_deps_json="$(json_array "$@")"
  fi

  ci_paths_json="[]"
  ci_present_bool="false"
  if [ -n "$CI_DEFS" ]; then
    ci_present_bool="true"
    set --
    for p in $(printf '%s' "$CI_DEFS" | sed '/^$/d' | sort -u); do set -- "$@" "$p"; done
    ci_paths_json="$(json_array "$@")"
  fi

  cont_paths_json="[]"
  if [ -n "$CONTAINER_DEFS" ]; then
    set --
    for p in $(printf '%s' "$CONTAINER_DEFS" | sed '/^$/d' | sort -u); do set -- "$@" "$p"; done
    cont_paths_json="$(json_array "$@")"
  fi

  readme_ev_json="[]"
  if [ -n "$READMES" ]; then
    set --
    for p in $READMES; do set -- "$@" "$(relpath "$p")"; done
    readme_ev_json="$(json_array "$@")"
  fi

  cat <<JSON
{
  "schema_version": "1.0",
  "generated_at": "$ts",
  "governance_version": {"governance_name": "$(json_escape "$GOV_NAME")", "version": "$(json_escape "$GOV_VER")"},
  "project_identity": {"name": "$(json_escape "$proj_name")", "repo_root": "."},
  "detections": {"languages": $det_langs_json, "dependency_managers": $det_deps_json, "ci_definition_paths": $ci_paths_json, "container_definition_paths": $cont_paths_json},
  "entrypoints": {"paths": [], "commands": [], "interfaces": [], "evidence_paths": $readme_ev_json},
  "automation_signals": {"ci_present": $ci_present_bool, "automation_paths": []},
  "verification_hooks": {
    "doctor_checks": [
      {"id": "doctor-command-executable", "pattern_id": "PAT-005-command-executable", "description": "Validate that any declared verification commands discovered from repo signals are executable.", "inputs": null, "success_criteria_notes": "Do not invent commands."},
      {"id": "doctor-configuration-valid", "pattern_id": "PAT-003-configuration-valid", "description": "Validate required configuration referenced by docs/CI/manifest exists and is syntactically valid.", "inputs": null, "success_criteria_notes": "Prefer in-repo validators when present."}
    ],
    "commands": []
  },
  "constraints": {"protected_paths": [], "notes": []},
  "unknowns": ["Canonical verification command unknown unless declared in repo signals."]
}
JSON
} | write_file "$MANIFEST_PATH"
track_created "system-manifest.json"
append_evidence_line "phase-3" "system_manifest_created" "profile=.governance/project-profile.json" "manifest_written=.governance/system-manifest.json" "high" "execution_layer"

# -------------------------
# Phase 4 — Guardrail Installation
# -------------------------
mkdir_p "$GOV_DIR/guardrails"
copy_file "$BOOTSTRAP_ROOT/guardrails/baseline-rules.yaml" "$GOV_DIR/guardrails/baseline-rules.yaml"
copy_file "$BOOTSTRAP_ROOT/guardrails/validation-patterns.yaml" "$GOV_DIR/guardrails/validation-patterns.yaml"
track_created "guardrails/baseline-rules.yaml"
track_created "guardrails/validation-patterns.yaml"
append_evidence_line "phase-4" "guardrails_vendored" "sources=bootstrap" "installed=.governance/guardrails/*" "high" "execution_layer"

# -------------------------
# Phase 5 — Task Governance Activation
# -------------------------
copy_file "$BOOTSTRAP_ROOT/agents/capability-registry.md" "$GOV_DIR/capability-registry.md"
copy_file "$BOOTSTRAP_ROOT/agents/session-start.md" "$GOV_DIR/session-start.md"
copy_file "$BOOTSTRAP_ROOT/bootstrap/evidence-spec.md" "$GOV_DIR/evidence-spec.md"
track_created "capability-registry.md"
track_created "session-start.md"
track_created "evidence-spec.md"

{
  cat <<'MD'
# Agent Runtime Governance (Project-Local)

## Mandatory Lifecycle
Interrogate → Validate → Plan → Execute → Verify → Learn

## Session Start
Agents must follow `.governance/session-start.md`.

## Guardrails and Validation Patterns
- `.governance/guardrails/baseline-rules.yaml`
- `.governance/guardrails/validation-patterns.yaml`

## Evidence Requirements
Record evidence under `.governance/evidence/` using `.governance/evidence-spec.md`.

## Refusal Criteria
Refuse or stop when:
- requested action violates guardrails
- action is destructive and explicit confirmation is not provided
- completion is requested but verification evidence cannot be produced
- stack assumptions would be introduced

## Project Manifests
- `.governance/project-profile.json`
- `.governance/system-manifest.json`
MD
} | write_file "$GOV_DIR/agent-runtime.md"
track_created "agent-runtime.md"
append_evidence_line "phase-5" "runtime_activated" "vendored_runtime_artifacts" "agent-runtime.md created" "high" "execution_layer"

# -------------------------
# Phase 6 — Learning System Initialization
# -------------------------
mkdir_p "$GOV_DIR/learning/incidents"
mkdir_p "$GOV_DIR/learning/proposals"
if [ "$DRY_RUN" -ne 1 ]; then
  track_created "learning/incidents/"
  track_created "learning/proposals/"
fi

{
  cat <<'MD'
# Governance Learning (Controlled Evolution)

Lifecycle (required): Incident → Analysis → Guardrail Proposal → Human Approval → Governance Update.

Records:
- Incidents: `.governance/learning/incidents/`
- Proposals: `.governance/learning/proposals/`

Explicit prohibition: agents must never auto-mutate governance rules or validation patterns.
MD
} | write_file "$GOV_DIR/learning/README.md"
track_created "learning/README.md"
append_evidence_line "phase-6" "learning_initialized" "learning_dirs_created" "learning README created" "high" "execution_layer"

# -------------------------
# Phase 7 — Governance Status Report
# -------------------------
{
  ts="$(iso_ts)"
  cat <<MD
# Governance Status Report

- Session: $SID
- Timestamp (UTC): $ts
- Governance version source: ../governance-version.json

## Created Governance Artifacts
$(printf '%b' "$CREATED_LIST" | sed '/^$/d' | sort | sed 's/^/- /')

## Evidence Summary
Evidence is recorded in: .governance/evidence/evidence.jsonl

## Non-Negotiable Statement
No application code was modified during bootstrap.
MD
} | write_file "$GOV_DIR/status.md"
track_created "status.md"
append_evidence_line "phase-7" "status_report_created" "status.md" "no_app_code_modified=true" "high" "execution_layer"

info "Done."
if [ "$DRY_RUN" -eq 1 ]; then info "(DRY-RUN) No files written."; fi
