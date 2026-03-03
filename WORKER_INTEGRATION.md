# Bootstrap Worker Integration

## Overview

This ai-governance-bootstrap repository provides a governance execution engine for external workers. Workers are registered via `worker.yaml` files and executed under bootstrap control with enforced gates and evidence recording.

## Architecture

### B-Mode Integration

Workers operate in **B-mode**:
- **Bootstrap** remains the monorepo governance engine
- **Workers** remain as separate external projects
- **Bootstrap** loads workers via absolute path reference
- **Governance** is controlled by bootstrap, not the worker

### Components

```
ai-governance-bootstrap/
├── runtime/
│   ├── worker_loader.py      # Discovers and loads worker.yaml files
│   ├── governance_context.py # Creates execution context for workers
│   ├── gates.py              # Implements G1-G4 governance gates
│   ├── manifest.py           # Generates governance manifests
│   ├── executor.py           # Main execution orchestration
│   └── cli.py                # Command-line interface
├── workers/
│   └── {worker_name}/
│       └── worker.yaml       # Worker registration
├── .governance/
│   ├── evidence/             # Evidence records per run
│   └── runs/                 # Run manifests and reports
└── run-bootstrap.py          # CLI entry point
```

## Worker Registration

### worker.yaml Format

```yaml
worker:
  name: worker_name
  description: Worker description

location:
  path: C:\path\to\worker  # Absolute path to worker project

execution:
  adapter_module: bootstrap.bootstrap_adapter
  language: python

phases:
  - phase1
  - phase2
  - phase3

governance:
  dry_run_supported: true
  evidence_required: true
  deterministic: true
```

### Worker Adapter

Workers must provide an adapter module at the specified `adapter_module` path. The adapter must implement:

```python
def run_phase(phase_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a phase within bootstrap governance context.
    
    Args:
        phase_name: Name of phase to execute
        context: Bootstrap governance context containing:
            - run_id: str
            - dry_run: bool
            - worker_path: str (where worker can write)
            - governance_dir: str (where bootstrap writes)
            - evidence_dir: str
            - Additional worker-specific parameters
    
    Returns:
        Dict containing:
            - success: bool
            - outputs: List[str] (paths written/planned)
            - evidence: List[Dict] (evidence items)
            - metadata: Dict (phase-specific data)
            - message: str (optional)
    """
```

## Execution

### Install Dependencies

```powershell
cd <BOOTSTRAP_ROOT>
pip install -r requirements.txt
```

### List Available Workers

```powershell
run-bootstrap list
```

### Show Worker Info

```powershell
run-bootstrap info --worker gmail_bill_intelligence
```

### Execute Worker (Dry-Run)

```powershell
run-bootstrap run --worker gmail_bill_intelligence --dry-run --since-weeks 6
```

**Dry-run mode:**
- No files created in worker data/ or reports/
- Only planned write evidence in .governance/
- All gates (G1-G4) are checked

### Execute Worker (Real Run)

```powershell
run-bootstrap run --worker gmail_bill_intelligence --since-weeks 6
```

**Real run:**
- Writes occur in worker data/ directory
- Governance artifacts in .governance/
- Manifest and evidence generated
- Gates enforced

## Governance

### Governance Context

Bootstrap provides each phase with a governance context containing:

- **run_id**: Unique run identifier
- **dry_run**: Boolean flag for dry-run mode
- **worker_path**: Where worker is allowed to write
- **governance_dir**: Where bootstrap writes governance artifacts
- **evidence_dir**: Where evidence is recorded
- **Worker-specific parameters** (e.g., since_weeks)

### Gates (G1-G4)

Bootstrap enforces four governance gates:

#### G1: Write Scope Enforcement

**Rule**: All writes must occur under:
- `worker_path` (worker's project directory)
- `bootstrap_root/.governance` (governance artifacts)

**Check**: Validates all planned/actual writes are within allowed scope.

**Failure**: Any write outside these paths fails the gate.

#### G2: Schema Validation Enforcement

**Rule**: All extracted JSON must validate against declared schemas.

**Check**: Verifies extraction outputs are schema-compliant.

**Failure**: Schema validation failures in extract/persist phases.

#### G3: Determinism Check

**Rule**: Re-running schedule generation without new input yields identical hashes.

**Check**: Validates output hashes are deterministic.

**Failure**: Missing output hash or non-deterministic outputs.

#### G4: Evidence Coverage

**Rule**: If a bill is not needs_review, then vendor, amount, due_date must have evidence pointers.

**Check**: Validates all extracted fields have evidence citations.

**Failure**: Missing evidence for extracted fields.

### Manifest

After execution, bootstrap generates:

**`.governance/runs/{run_id}/manifest.json`**
```json
{
  "run_id": "...",
  "timestamp_utc": "...",
  "worker": {...},
  "execution": {
    "dry_run": false,
    "parameters": {...},
    "phases": [...]
  },
  "statistics": {
    "emails_scanned": 0,
    "candidates_count": 0,
    ...
  },
  "governance": {
    "gates": {...},
    "all_gates_passed": true,
    "evidence_items_count": 0
  },
  "outputs": [...],
  "phases": {...}
}
```

**`.governance/evidence/{run_id}/evidence.jsonl`**

Append-only JSONL file with one evidence item per line.

**`.governance/runs/{run_id}/gate_report.txt`**

Human-readable gate results report.

## Worker Implementation Requirements

### Phase Function Contract

Each phase function must:

1. **Accept context**: Receive bootstrap governance context as dict
2. **Return result**: Return dict with success, outputs, evidence, metadata
3. **Record writes**: List all files that will be/were written in `outputs`
4. **Provide evidence**: Include evidence items for verifiability
5. **Handle dry-run**: Respect `context["dry_run"]` flag

### Example Phase Implementation

```python
def run(context: Dict[str, Any]) -> Dict[str, Any]:
    dry_run = context["dry_run"]
    worker_path = Path(context["worker_path"])
    
    outputs = []
    evidence = []
    
    # Phase logic here
    if not dry_run:
        # Actually write files
        output_file = worker_path / "data" / "output.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(data))
        outputs.append(str(output_file))
    else:
        # Just record what would be written
        outputs.append(str(worker_path / "data" / "output.json"))
    
    # Record evidence
    evidence.append({
        "phase": "phase_name",
        "action": "what was done",
        "input": "what was processed",
        "result": "outcome",
        "confidence": "high"
    })
    
    return {
        "success": True,
        "outputs": outputs,
        "evidence": evidence,
        "metadata": {
            "items_processed": len(data)
        },
        "message": "Phase completed successfully"
    }
```

## Registered Workers

### gmail_bill_intelligence

Gmail invoice extraction and bill scheduling worker.

- **Location (relative)**: `../gmail-bills`
- **Phases**: ingest, classify, parse_attachments, extract, persist, schedule, alerts
- **Language**: Python

Execute with:
```powershell
run-bootstrap run --worker gmail_bill_intelligence --dry-run --since-weeks 6
```

## Troubleshooting

### Worker not found

```
✗ Worker 'worker_name' not found.
```

**Solution**: Check that `workers/{worker_name}/worker.yaml` exists and is valid YAML.

### Failed to import adapter module

```
Failed to import adapter module 'bootstrap.bootstrap_adapter' from worker...
```

**Solution**: 
1. Verify worker path is correct in worker.yaml
2. Ensure adapter module exists at specified path
3. Check that worker has `__init__.py` files in package structure

### Gate G1 failure (write scope violation)

```
G1: ✗ FAIL
Write scope violations: N files outside allowed paths
```

**Solution**: Worker attempted to write outside worker_path or .governance/. Review worker code to ensure all writes are within allowed scope.

### Module import errors

```
ModuleNotFoundError: No module named 'yaml'
```

**Solution**: Install bootstrap dependencies:
```powershell
pip install -r requirements.txt
```

## Development

### Adding a New Worker

1. Create worker registration:
   ```powershell
   mkdir workers\new_worker_name
   # Create worker.yaml
   ```

2. Implement worker adapter in external project:
   ```python
   # {worker_path}/bootstrap/bootstrap_adapter.py
   def run_phase(phase_name, context):
       # Implementation
       pass
   ```

3. Test with dry-run:
   ```powershell
  run-bootstrap run --worker new_worker_name --dry-run
   ```

4. Execute real run:
   ```powershell
  run-bootstrap run --worker new_worker_name
   ```

### Extending Gates

To add additional gates, edit `runtime/gates.py`:

```python
def check_g5_custom_rule(context, worker_path, bootstrap_root):
    # Implementation
    return GateResult(
        gate_name="G5",
        passed=True,
        message="Custom rule passed",
        details={}
    )

# Add to run_gates function
def run_gates(context, worker_path, bootstrap_root):
    results = []
    results.append(check_g1_write_scope(...))
    results.append(check_g2_schema_validation(...))
    results.append(check_g3_determinism(...))
    results.append(check_g4_evidence_coverage(...))
    results.append(check_g5_custom_rule(...))  # Add new gate
    # ...
```

## Design Principles

### Separation of Concerns

- **Bootstrap**: Governance, gates, manifests, evidence
- **Worker**: Domain logic, data processing, business rules

### No Governance Leakage

Workers must NOT:
- Implement their own gate logic
- Create their own manifests
- Control governance directories
- Make governance decisions

### Minimal Integration Surface

Workers only need:
- `worker.yaml` registration
- `bootstrap_adapter.py` with `run_phase` function
- Respect for governance context parameters

### Path-Based Governance

- Workers write to their own directories
- Bootstrap writes to `.governance/`
- Gate G1 enforces boundary
- No complex permission systems needed
