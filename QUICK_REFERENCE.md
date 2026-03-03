# Bootstrap Quick Reference

## Command Cheat Sheet

```powershell
# List workers
run-bootstrap list

# Health check (no auto-fix)
run-bootstrap doctor

# Determinism safety harness (no writes)
run-bootstrap selftest --worker gmail_bill_intelligence

# Worker info
run-bootstrap info --worker gmail_bill_intelligence

# Dry-run (no writes)
run-bootstrap run --worker gmail_bill_intelligence --dry-run --since-weeks 6

# Real run
run-bootstrap run --worker gmail_bill_intelligence --since-weeks 6
```

## Exit Codes

- `0` - Success (all gates passed)
- `1` - Execution error (gate failure)
- `2` - Unexpected error

## Governance Gates

| Gate | What It Checks | Failure Means |
|------|---------------|---------------|
| **G1** | Write scope | Files written outside allowed paths |
| **G2** | Schema validation | Extracted data doesn't validate |
| **G3** | Determinism | Outputs are non-deterministic |
| **G4** | Evidence coverage | Missing evidence for claims |

## Allowed Write Paths

✓ **Worker can write to**:
- Its runtime directory (default: worker repo root)
- If `WORKER_RUNTIME_DIR` is set: that directory (e.g., `<LOCAL_RUNTIME_ROOT>\\gmail-bills\\...`)

✗ **Worker CANNOT write to**:
- Bootstrap directories
- System directories
- Other workers' directories

✓ **Bootstrap writes to**:
- Governance directory (default: `<BOOTSTRAP_ROOT>\.governance\...`)
- If `BOOTSTRAP_GOVERNANCE_DIR` is set: that directory

## Phase Function Contract

```python
def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Args:
        context: {
            "run_id": str,
            "dry_run": bool,
            "worker_path": str,
            "governance_dir": str,
            "evidence_dir": str,
            "since_weeks": int,  # worker-specific
        }
    
    Returns: {
        "success": bool,
        "outputs": List[str],      # Paths written
        "evidence": List[Dict],    # Evidence items
        "metadata": Dict,          # Phase data
        "message": str             # Status message
    }
    """
```

## Evidence Item Template

```python
{
    "phase": "phase_name",
    "action": "what was done",
    "input": "what was processed",
    "result": "outcome",
    "confidence": "high|medium|low",
    "source": "where it came from"
}
```

## Governance Context Structure

Workers receive this dict:

```python
{
    "run_id": "worker_20260302_123456_abc123",
    "worker_name": "gmail_bill_intelligence",
    "worker_path": "<WORKER_ROOT>",
    "bootstrap_root": "<BOOTSTRAP_ROOT>",
    "governance_dir": "<BOOTSTRAP_GOVERNANCE_DIR or <BOOTSTRAP_ROOT>\\.governance>",
    "evidence_dir": "<governance_dir>\\evidence\\{run_id}",
    "dry_run": False,
    "timestamp_utc": "2026-03-02T12:34:56+00:00",
    "since_weeks": 6,  # worker parameters
}
```

## Worker Registration (worker.yaml)

```yaml
worker:
  name: my_worker
  description: One-line description

location:
  # Relative to the bootstrap repo root (absolute paths are rejected)
  path: ../gmail-bills

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

## Adapter Implementation

In worker project at `bootstrap/bootstrap_adapter.py`:

```python
from typing import Dict, Any

def run_phase(phase_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
    # Import phases lazily
    from app.pipeline import phase_01_ingest
    
    PHASE_MAP = {
        "ingest": phase_01_ingest.run,
        # ... more phases
    }
    
    if phase_name not in PHASE_MAP:
        raise ValueError(f"Unknown phase: {phase_name}")
    
    return PHASE_MAP[phase_name](context)
```

## Dry-Run vs Real Run

| Aspect | Dry-Run | Real Run |
|--------|---------|----------|
| Worker writes | ✗ No files created | ✓ Files created |
| Bootstrap writes | ✓ Governance only | ✓ Governance only |
| Phase execution | ✓ Logic runs | ✓ Logic runs |
| Gates checked | ✓ G1-G4 | ✓ G1-G4 |
| Manifest created | ✓ Yes | ✓ Yes |
| `outputs` in result | Planned paths | Actual paths |

## Artifacts Generated

After execution, find artifacts at:

```
.governance/
├── runs/
│   └── {run_id}/
│       ├── manifest.json       # Execution summary
│       └── gate_report.txt     # Human-readable gates
└── evidence/
    └── {run_id}/
        └── evidence.jsonl      # Evidence items (JSONL)
```

## Manifest Structure

```json
{
  "run_id": "...",
  "timestamp_utc": "...",
  "worker": { "name": "...", "description": "...", "path": "..." },
  "execution": { "dry_run": false, "parameters": {...}, "phases": [...] },
  "statistics": {
    "emails_scanned": 0,
    "candidates_count": 0,
    "bills_extracted": 0,
    "bills_persisted": 0,
    "needs_review_count": 0,
    "errors_count": 0
  },
  "governance": {
    "gates": { "G1": {...}, "G2": {...}, "G3": {...}, "G4": {...} },
    "all_gates_passed": true,
    "evidence_items_count": 0
  },
  "outputs": [
    { "path": "...", "sha256": "..." }
  ],
  "phases": {
    "ingest": { "success": true, "metadata": {...} },
    "classify": { "success": true, "metadata": {...} }
  }
}
```

## Common Issues

### 🔴 Worker not found

**Fix**: Check `workers/{worker}/worker.yaml` exists

### 🔴 Failed to import adapter

**Fix**: Verify `bootstrap/bootstrap_adapter.py` exists in worker

### 🔴 G1 failure (write scope)

**Fix**: Worker writing outside allowed paths. Check `outputs` list in phase results.

### 🔴 ModuleNotFoundError: yaml

**Fix**: `python -m pip install PyYAML`

## Development Workflow

1. **Register worker**: Create `worker.yaml` in `workers/{name}/`
2. **Implement adapter**: Create `bootstrap/bootstrap_adapter.py` in worker
3. **Implement phases**: Create phase modules in worker
4. **Test dry-run**: `run-bootstrap run --worker {name} --dry-run`
5. **Check gates**: Review gate report for failures
6. **Test real run**: `run-bootstrap run --worker {name}`
7. **Verify outputs**: Check worker outputs and governance artifacts

## Debugging

### See what workers are registered
```powershell
run-bootstrap list
```

### Check worker configuration
```powershell
run-bootstrap info --worker {name}
```

### Dry-run to see planned operations
```powershell
run-bootstrap run --worker {name} --dry-run
```

### Check last run's gate report
```powershell
cd .governance\runs
ls -r | sort LastWriteTime | select -last 1
cat {run_id}\gate_report.txt
```

### Check last run's manifest
```powershell
cat {run_id}\manifest.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### Check last run's evidence
```powershell
cd .governance\evidence\{run_id}
cat evidence.jsonl
```

## File Structure

```
ai-governance-bootstrap/
├── runtime/               # Execution engine
│   ├── worker_loader.py
│   ├── governance_context.py
│   ├── gates.py
│   ├── manifest.py
│   ├── executor.py
│   └── cli.py
├── workers/               # Worker registrations
│   └── {worker}/
│       └── worker.yaml
├── .governance/           # Generated artifacts
│   ├── evidence/
│   └── runs/
└── run-bootstrap.py       # CLI entry point

{worker-project}/
├── bootstrap/
│   └── bootstrap_adapter.py    # Integration adapter
├── app/
│   └── pipeline/              # Worker implementation
│       ├── phase_01_*.py
│       ├── phase_02_*.py
│       └── ...
├── data/                      # Worker writes here
└── reports/                   # Worker reports here
```

## Key Principles

1. **Bootstrap controls governance** - Workers implement domain logic
2. **Path reference, not copy** - Worker stays in its own directory
3. **Single function interface** - Only `run_phase()` required
4. **Evidence everything** - Every claim needs a citation
5. **Gates are final** - Failed gate = failed execution
6. **Dry-run first** - Always test with `--dry-run` before real run

## See Also

- [README.md](README.md) - Overview and setup
- [WORKER_INTEGRATION.md](WORKER_INTEGRATION.md) - Detailed integration guide
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Testing procedures
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - What was built
