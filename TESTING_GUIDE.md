# Bootstrap Integration - Testing Guide

## Prerequisites

### Install Python

1. Download Python 3.11+ from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"
3. Verify installation:
   ```powershell
   python --version
   ```

### Install Bootstrap Dependencies

```powershell
cd <BOOTSTRAP_ROOT>
python -m pip install -r requirements.txt
```

Expected output:
```
Successfully installed PyYAML-6.x
```

## Test Plan

## Cross-Machine Validation Protocol (Windows)

Run the same steps on both machines to confirm the system behaves identically across Windows user profiles.

1. Install Python 3.11 (required for deterministic runtime)
2. Delete and recreate the venv (venvs must be local per machine)
  ```powershell
  cd <BOOTSTRAP_ROOT>
  Remove-Item -Recurse -Force .\.venv
  py -3.11 -m venv .venv
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  python -m pip install -e .
  ```
3. (Optional) Move runtime artifacts off OneDrive
  ```powershell
  setx WORKER_RUNTIME_DIR C:\dev-runtime\gmail-bills
  setx BOOTSTRAP_GOVERNANCE_DIR C:\dev-runtime\bootstrap-governance
  ```
  Reopen your terminal after `setx`.
4. Validate health and determinism
  ```powershell
  run-bootstrap doctor
  run-bootstrap selftest --worker gmail_bill_intelligence
  ```
  The schedule/ledger hashes printed by selftest must match between machines.

### Test 1: Worker Discovery

**Objective**: Verify bootstrap can discover registered workers.

```powershell
cd <BOOTSTRAP_ROOT>
run-bootstrap list
```

**Expected output**:
```
Registered Workers (1):
============================================================

gmail_bill_intelligence
  Description: Gmail invoice extraction and bill scheduling worker
  Location: <WORKER_ROOT>
  Phases: ingest, classify, parse_attachments, extract, persist, schedule, alerts
  Dry-run supported: Yes
```

**Pass**: Worker is listed
**Fail**: Error message or no workers found

---

### Test 2: Worker Info

**Objective**: Verify bootstrap can read worker configuration.

```powershell
run-bootstrap info --worker gmail_bill_intelligence
```

**Expected output**:
```
Worker: gmail_bill_intelligence
============================================================
Description: Gmail invoice extraction and bill scheduling worker
Location: <WORKER_ROOT>
Language: python
Adapter module: bootstrap.bootstrap_adapter

Phases:
  - ingest
  - classify
  - parse_attachments
  - extract
  - persist
  - schedule
  - alerts

Governance:
  Dry-run supported: Yes
  Evidence required: Yes
  Deterministic: Yes
```

**Pass**: Worker info displayed correctly
**Fail**: Error or missing information

---

### Test 3: Dry-Run Execution

**Objective**: Verify worker executes in dry-run mode with no actual writes.

```powershell
run-bootstrap run --worker gmail_bill_intelligence --dry-run --since-weeks 6
```

**Expected output**:
```
============================================================
Bootstrap Execution: gmail_bill_intelligence
============================================================
Mode: DRY-RUN
Since: 6 weeks

[1/6] Loading worker configuration...
  Worker: gmail_bill_intelligence
  Description: Gmail invoice extraction and bill scheduling worker
  Location: <WORKER_ROOT>
  Phases: ingest, classify, parse_attachments, extract, persist, schedule, alerts

[2/6] Creating governance context...
  Run ID: gmail_bill_intelligence_YYYYMMDD_HHMMSS_XXXXXXXX
  Governance dir: <BOOTSTRAP_GOVERNANCE_DIR or <BOOTSTRAP_ROOT>\\.governance>

[3/6] Loading worker adapter...
  Adapter module: bootstrap.bootstrap_adapter

[4/6] Executing phases...
  Phase 1/7: ingest
    ✓ Ingested 5 emails with 3 attachments
  Phase 2/7: classify
    ✓ Classified 3 bill candidates
  Phase 3/7: parse_attachments
    ✓ Parsed 3 attachments
  Phase 4/7: extract
    ✓ Extracted 3 bills (0 need review)
  Phase 5/7: persist
    ✓ Persisted 3 bills to ledger
  Phase 6/7: schedule
    ✓ Generated bill schedule
  Phase 7/7: alerts
    ✓ Generated alerts

[5/6] Running governance gates...
  ✓ G1: All N writes within allowed scope
  ✓ G2: All schema validations passed
  ✓ G3: Schedule output is deterministic (hash: ...)
  ✓ G4: Evidence coverage complete (9 fields)

[6/6] Creating governance artifacts...
  ✓ Manifest: C:\...\ai-governance-bootstrap\.governance\runs\...\manifest.json
  ✓ Evidence: C:\...\ai-governance-bootstrap\.governance\evidence\...\evidence.jsonl

============================================================
✓ Execution complete - ALL GATES PASSED
============================================================
```

**Verify**:
1. No files created in `<WORKER_RUNTIME_DIR or <WORKER_ROOT>\data\>`
2. No files created in `<WORKER_RUNTIME_DIR or <WORKER_ROOT>\reports\>`
3. Governance artifacts created in `.governance/`
4. All gates passed (G1-G4)

**Pass criteria**:
- ✓ All phases execute successfully
- ✓ No errors reported
- ✓ All gates pass (G1-G4)
- ✓ Governance artifacts created
- ✓ No worker data/reports created

**Fail criteria**:
- ✗ Any phase fails
- ✗ Any gate fails
- ✗ Files created in worker directories during dry-run

---

### Test 4: Real Run Execution

**Objective**: Verify worker executes with actual writes.

```powershell
run-bootstrap run --worker gmail_bill_intelligence --since-weeks 6
```

**Expected output**:
Similar to Test 3, but with "Mode: REAL RUN"

**Verify**:
1. Files created in `<WORKER_RUNTIME_DIR or <WORKER_ROOT>\data\>`:
   - `raw_emails/` directory exists
   - `attachments/` directory exists
   - `extracted_text/` directory exists
   - `ledger/extracted/` directory exists
   - `ledger/alerts.json` exists

2. Files created in `<WORKER_RUNTIME_DIR or <WORKER_ROOT>\reports\>`:
   - `bills_schedule.md` exists

3. Governance artifacts in `.governance/`:
   - `runs/{run_id}/manifest.json` exists
   - `evidence/{run_id}/evidence.jsonl` exists
   - `runs/{run_id}/gate_report.txt` exists

**Pass criteria**:
- ✓ All phases execute successfully
- ✓ Worker outputs created in correct locations
- ✓ All gates pass (G1-G4)
- ✓ Governance artifacts created
- ✓ Manifest contains correct statistics

**Fail criteria**:
- ✗ Any phase fails
- ✗ Any gate fails
- ✗ Files created outside allowed paths (G1 violation)

---

### Test 5: G1 Write Scope Enforcement

**Objective**: Verify G1 gate prevents writes outside allowed scope.

**Manual test**: Modify a phase to attempt writing outside worker_path and .governance/.

Edit `<WORKER_ROOT>\app\pipeline\phase_01_ingest.py`:

```python
# Add this after line defining outputs
bad_path = Path("C:/temp/bad_write.txt")
outputs.append(str(bad_path))
```

Run:
```powershell
run-bootstrap run --worker gmail_bill_intelligence --dry-run
```

**Expected output**:
```
[5/6] Running governance gates...
  ✗ G1: Write scope violations: 1 files outside allowed paths
  ✓ G2: All schema validations passed
  ✓ G3: Schedule output is deterministic
  ✓ G4: Evidence coverage complete

============================================================
✗ Execution complete - GATE FAILURES DETECTED
============================================================

Gate report shows:
G1: ✗ FAIL
  Write scope violations: 1 files outside allowed paths
  violations:
    - C:\temp\bad_write.txt
```

**Pass**: G1 fails and execution exits with error
**Fail**: G1 passes or execution completes

**Cleanup**: Revert the change to phase_01_ingest.py

---

### Test 6: Manifest Validation

**Objective**: Verify manifest contains correct structure and data.

After running Test 4 (real run), inspect the manifest:

```powershell
# Find the latest run directory
cd <BOOTSTRAP_GOVERNANCE_DIR or <BOOTSTRAP_ROOT>\.governance>\runs
ls -r | sort LastWriteTime | select -last 1

# View manifest
cat {run_id}\manifest.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

**Verify manifest contains**:
- `run_id`: String
- `timestamp_utc`: ISO datetime
- `worker`: Object with name, description, path
- `execution`: Object with dry_run, parameters, phases
- `statistics`: Object with counts (emails_scanned, candidates_count, etc.)
- `governance`: Object with gates results, all_gates_passed
- `outputs`: Array of file paths with sha256 hashes
- `phases`: Object with phase results

**Pass**: All expected fields present and correct
**Fail**: Missing fields or incorrect data

---

### Test 7: Evidence Recording

**Objective**: Verify evidence is recorded in JSONL format.

After Test 4, inspect evidence:

```powershell
cd <BOOTSTRAP_GOVERNANCE_DIR or <BOOTSTRAP_ROOT>\.governance>\evidence\{run_id}
cat evidence.jsonl
```

**Verify**:
- File exists
- Contains multiple lines
- Each line is valid JSON
- Each evidence item has: phase, action, input, result, confidence, source

**Pass**: Evidence file valid and contains items from all phases
**Fail**: File missing, invalid JSON, or missing required fields

---

### Test 8: Determinism Check (G3)

**Objective**: Verify schedule generation is deterministic.

Run twice without changes:

```powershell
run-bootstrap run --worker gmail_bill_intelligence --since-weeks 6
# Note the schedule hash from G3 gate

run-bootstrap run --worker gmail_bill_intelligence --since-weeks 6
# Note the second schedule hash
```

**Expected**: Both runs report same schedule hash in G3 gate.

**Pass**: Hashes match
**Fail**: Hashes differ

---

## Acceptance Criteria Summary

✓ **DRY-RUN**:
- [ ] No files created in gmail-bills/data/ or reports/
- [ ] Only planned evidence in .governance/
- [ ] Exits PASS G1–G4

✓ **REAL RUN**:
- [ ] bills.db created (or planned)
- [ ] bills_schedule.md created
- [ ] alerts.json created
- [ ] Manifest and evidence present
- [ ] Gates pass

✓ **RE-RUN DETERMINISM**:
- [ ] Schedule generation yields identical schedule hash

## Troubleshooting

### ImportError: No module named 'yaml'

**Solution**:
```powershell
python -m pip install PyYAML
```

### Worker 'gmail_bill_intelligence' not found

**Solution**: Verify worker.yaml exists at:
```
<BOOTSTRAP_ROOT>\workers\gmail_bill_intelligence\worker.yaml
```

### Failed to import adapter module

**Solution**: Verify bootstrap_adapter.py exists at:
```
<WORKER_ROOT>\bootstrap\bootstrap_adapter.py
```

### G1 failures in real run

**Cause**: Worker attempting to write outside allowed paths.

**Solution**: Review phase implementations to ensure all writes target:
- `context["worker_path"]/*` (worker data)
- Never write to bootstrap directories except .governance/

## Quick Verification Script

```powershell
# Run all tests sequentially
cd <BOOTSTRAP_ROOT>

Write-Host "Test 1: Worker Discovery" -ForegroundColor Cyan
run-bootstrap list

Write-Host "`nTest 2: Worker Info" -ForegroundColor Cyan
run-bootstrap info --worker gmail_bill_intelligence

Write-Host "`nTest 3: Dry-Run Execution" -ForegroundColor Cyan
run-bootstrap run --worker gmail_bill_intelligence --dry-run --since-weeks 6

Write-Host "`nTest 4: Real Run Execution" -ForegroundColor Cyan
run-bootstrap run --worker gmail_bill_intelligence --since-weeks 6

Write-Host "`nAll tests complete!" -ForegroundColor Green
```

Save this as `test-integration.ps1` and run:
```powershell
.\test-integration.ps1
```
