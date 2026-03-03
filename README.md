# AI Governance Bootstrap

## Quick Start

### Prerequisites

1. **Python 3.11+** installed and in PATH
2. **PyYAML** package

```powershell
python -m pip install -r requirements.txt
```

### Run a Worker

```powershell
# List available workers
run-bootstrap list

# Show worker details
run-bootstrap info --worker gmail_bill_intelligence

# Execute worker (dry-run)
run-bootstrap run --worker gmail_bill_intelligence --dry-run --since-weeks 6

# Execute worker (real run)
run-bootstrap run --worker gmail_bill_intelligence --since-weeks 6

# Health check (no auto-fix)
run-bootstrap doctor

# Determinism safety harness (no writes)
run-bootstrap selftest --worker gmail_bill_intelligence
```

## What This Is

This repository implements **governance execution infrastructure** for AI-assisted software engineering workers.

**It is NOT**:
- Enterprise risk management
- Compliance framework
- Organizational policy system

**It IS**:
- Worker execution orchestration
- Governance gate enforcement (G1-G4)
- Evidence and manifest generation
- Deterministic execution control

## Architecture

### Bootstrap Engine (This Repo)

```
ai-governance-bootstrap/
├── runtime/           # Execution engine
│   ├── worker_loader.py
│   ├── governance_context.py
│   ├── gates.py
│   ├── manifest.py
│   ├── executor.py
│   └── cli.py
├── workers/           # Worker registrations
│   └── {worker}/
│       └── worker.yaml
└── .governance/       # Governance artifacts (generated)
    ├── evidence/
    └── runs/
```

### Workers (External Projects)

Workers are **separate projects** registered by a *relative* path in `workers/{worker}/worker.yaml`.

Example (sibling repo): `../gmail-bills`

```
gmail-bills/
├── bootstrap/
│   └── bootstrap_adapter.py  # Integration adapter
├── app/
│   └── pipeline/             # Worker implementation
│       ├── phase_01_ingest.py
│       ├── phase_02_classify.py
│       └── ...
├── data/                     # Worker writes here
└── reports/                  # Worker reports here
```

## B-Mode Integration

**Bootstrap** controls governance. **Workers** implement domain logic.

**Separation**:
- Bootstrap: Gates, manifests, evidence
- Workers: Business logic, data processing
- **NO** governance logic in workers
- **NO** worker code in bootstrap

**Integration point**: `bootstrap_adapter.py` in worker project.

## Governance Gates

### G1: Write Scope Enforcement

**Rule**: Worker may only write to:
- Its own project directory
- Bootstrap `.governance/` (via bootstrap, not directly)

**Enforcement**: Bootstrap validates all file paths before marking run as passed.

**Failure**: Any write outside allowed paths → G1 FAIL → execution error.

### G2: Schema Validation Enforcement

**Rule**: All extracted JSON must validate against declared schemas.

**Enforcement**: Worker phases report schema validation results. Bootstrap checks for failures.

**Failure**: Schema validation failure in extract/persist phases → G2 FAIL.

### G3: Determinism Check

**Rule**: Re-running schedule generation yields identical output hash.

**Enforcement**: Worker reports output hash. Bootstrap verifies hash is provided.

**Failure**: Missing or non-deterministic hash → G3 FAIL.

### G4: Evidence Coverage

**Rule**: Non-review items must have evidence for all key fields.

**Enforcement**: Worker reports evidence coverage. Bootstrap checks for missing coverage.

**Failure**: Missing evidence for extracted fields → G4 FAIL.

## CLI Commands

### List Workers

```powershell
run-bootstrap list
```

Shows all registered workers with descriptions and phases.

### Show Worker Info

```powershell
run-bootstrap info --worker <worker_name>
```

Displays detailed worker configuration.

### Execute Worker

```powershell
run-bootstrap run --worker <worker_name> [options]
```

### Doctor

```powershell
run-bootstrap doctor
```

Prints:
- Python version
- Venv path
- Bootstrap root path
- Worker resolved path
- Resolved `WORKER_RUNTIME_DIR` and `BOOTSTRAP_GOVERNANCE_DIR`
- PASS/WARN/FAIL summary (WARN for OneDrive)

### Selftest

```powershell
run-bootstrap selftest --worker <worker_name>
```

Runs the worker twice (dry-run, no artifacts) and compares `schedule_hash` + `ledger_hash`.

**Options**:
- `--dry-run`: Execute in dry-run mode (no actual writes)
- `--since-weeks <N>`: Worker-specific parameter (e.g., for gmail-bills)
- `--bootstrap-root <path>`: Override bootstrap root path (auto-detected)

**Exit codes**:
- `0`: Success (all gates passed)
- `1`: Execution error (gate failure)
- `2`: Unexpected error

## Execution Flow

1. **Load worker**: Read `workers/{worker}/worker.yaml`
2. **Create context**: Generate run ID, set up governance directories
3. **Load adapter**: Import worker's `bootstrap_adapter.py` dynamically
4. **Execute phases**: Run each phase sequentially with governance context
5. **Run gates**: Check G1-G4 after all phases complete
6. **Generate artifacts**: Create manifest, evidence, and gate report
7. **Report**: Print summary and exit with appropriate code

## Governance Artifacts

After execution, bootstrap creates:

### Manifest

**Path**: `.governance/runs/{run_id}/manifest.json`

Contains:
- Run metadata (ID, timestamp, worker)
- Execution parameters
- Statistics (emails scanned, bills extracted, etc.)
- Gate results (G1-G4)
- Output file hashes
- Phase summaries

### Evidence

**Path**: `.governance/evidence/{run_id}/evidence.jsonl`

JSONL file with evidence items:
- Phase name
- Action performed
- Input/output
- Confidence level
- Source

### Gate Report

**Path**: `.governance/runs/{run_id}/gate_report.txt`

Human-readable report of gate results.

## Worker Registration

### Create worker.yaml

```yaml
worker:
  name: my_worker
  description: Worker description

location:
    # Relative to the bootstrap repo root (absolute paths are rejected)
    path: ../my-worker

execution:
  adapter_module: bootstrap.bootstrap_adapter
  language: python

phases:
  - phase1
  - phase2

governance:
  dry_run_supported: true
  evidence_required: true
  deterministic: true
```

### Implement Adapter

In worker project at `bootstrap/bootstrap_adapter.py`:

```python
def run_phase(phase_name: str, context: dict) -> dict:
    """
    Execute a phase.
    
    Args:
        phase_name: Name of phase to execute
        context: Governance context from bootstrap
    
    Returns:
        {
            "success": bool,
            "outputs": [str],  # Files written/planned
            "evidence": [dict],  # Evidence items
            "metadata": dict,  # Phase-specific data
            "message": str
        }
    """
    # Implementation
    pass
```

### Register Worker

1. Create `workers/{worker_name}/` directory
2. Add `worker.yaml` with configuration
3. Worker automatically discovered on next run

## Development

### Adding New Gates

Edit `runtime/gates.py`:

```python
def check_g5_custom_rule(context, worker_path, bootstrap_root):
    # Check logic
    return GateResult(
        gate_name="G5",
        passed=True,
        message="Custom rule passed",
        details={}
    )

# Add to run_gates()
def run_gates(context, worker_path, bootstrap_root):
    results = [
        check_g1_write_scope(...),
        check_g2_schema_validation(...),
        check_g3_determinism(...),
        check_g4_evidence_coverage(...),
        check_g5_custom_rule(...),  # New gate
    ]
    return all(r.passed for r in results), results
```

### Extending Context

Edit `runtime/governance_context.py` to add new context fields:

```python
class GovernanceContext:
    def __init__(self, ...):
        # Add new fields
        self.custom_param = custom_value
    
    def to_dict(self):
        return {
            # Add to dict passed to workers
            "custom_param": self.custom_param,
            ...
        }
```

## Documentation

- [WORKER_INTEGRATION.md](WORKER_INTEGRATION.md) - Detailed integration guide
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Complete testing procedures
- [bootstrap/BOOTSTRAP_IDENTITY.md](bootstrap/BOOTSTRAP_IDENTITY.md) - Bootstrap identity
- [bootstrap/BOOTSTRAP_PROMPT.md](bootstrap/BOOTSTRAP_PROMPT.md) - Bootstrap protocol
- [runtime/bootstrap-execution-spec.md](runtime/bootstrap-execution-spec.md) - Execution spec

## Registered Workers

### gmail_bill_intelligence

Gmail invoice and bill extraction worker.

**Execute**:
```powershell
run-bootstrap run --worker gmail_bill_intelligence --dry-run --since-weeks 6
```

**Phases**:
1. ingest - Fetch emails from Gmail
2. classify - Identify bill candidates
3. parse_attachments - Extract text from PDFs/images
4. extract - Extract structured bill data
5. persist - Save to SQLite ledger
6. schedule - Generate bill schedule
7. alerts - Generate alerts JSON

**Outputs**:
- `gmail-bills/data/` - Raw emails, attachments, extracted text, ledger
- `gmail-bills/reports/` - Bill schedule markdown

## Troubleshooting

### Python not found

**Symptoms**: `Python was not found`

**Solution**: Install Python 3.11+ from https://www.python.org/ and add to PATH.

### PyYAML not installed

**Symptoms**: `ModuleNotFoundError: No module named 'yaml'`

**Solution**:
```powershell
python -m pip install PyYAML
```

### Worker not found

**Symptoms**: `Worker 'X' not found`

**Solution**: 
1. Verify `workers/{worker}/worker.yaml` exists
2. Check YAML syntax is valid
3. Verify `location.path` is correct absolute path

### Adapter import failed

**Symptoms**: `Failed to import adapter module 'bootstrap.bootstrap_adapter'`

**Solution**:
1. Verify worker path exists
2. Check `bootstrap/bootstrap_adapter.py` exists in worker
3. Ensure `bootstrap/__init__.py` exists
4. Check Python syntax in adapter

### G1 gate failure

**Symptoms**: `G1: ✗ FAIL - Write scope violations`

**Cause**: Worker attempted to write outside allowed paths.

**Solution**: Review worker phase implementations. All writes must be under:
- `context["worker_path"]` (worker's directory)
- Don't write directly to bootstrap directories

## License

See repository root for license information.

## Contact

For issues or questions about bootstrap integration, see documentation or create an issue.
