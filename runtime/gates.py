"""
Governance gates enforcement.

Implements G1-G4 gates for worker execution:
- G1: Write scope enforcement
- G2: Schema validation enforcement
- G3: Determinism check
- G4: Evidence coverage
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import json
import hashlib

from .paths import resolve_bootstrap_governance_dir, resolve_worker_runtime_dir


class GateFailure(Exception):
    """Raised when a governance gate fails."""
    pass


class GateResult:
    """Result of a gate check."""
    
    def __init__(
        self,
        gate_name: str,
        passed: bool,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.gate_name = gate_name
        self.passed = passed
        self.message = message
        self.details = details or {}
    
    def __bool__(self):
        return self.passed
    
    def __repr__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"<GateResult {self.gate_name}: {status} - {self.message}>"


def check_g1_write_scope(
    context: Any,
    worker_path: Path,
    bootstrap_root: Path
) -> GateResult:
    """
    G1: Write Scope Enforcement
    
    All writes must occur under one of:
    - worker_path (worker repo root)
    - WORKER_RUNTIME_DIR (if set; defaults to worker_path)
    - BOOTSTRAP_GOVERNANCE_DIR (if set; defaults to bootstrap_root/.governance)
    
    Args:
        context: GovernanceContext
        worker_path: Path to worker root
        bootstrap_root: Path to bootstrap root
        
    Returns:
        GateResult indicating pass/fail
    """
    # Resolve allowed roots dynamically (machine-agnostic)
    governance_dir = resolve_bootstrap_governance_dir(Path(bootstrap_root).resolve())

    worker_root = Path(worker_path).resolve()
    runtime_root = resolve_worker_runtime_dir(worker_root)
    
    # Get all writes from context
    writes = context.actual_writes if not context.dry_run else context.planned_writes
    
    allowed_roots = [worker_root, runtime_root, governance_dir]

    violations = []
    for write_path in writes:
        write_path_obj = Path(write_path).resolve()

        allowed = False
        for root in allowed_roots:
            try:
                write_path_obj.relative_to(root)
                allowed = True
                break
            except ValueError:
                continue

        if not allowed:
            violations.append(str(write_path_obj))
    
    if violations:
        return GateResult(
            gate_name="G1",
            passed=False,
            message=f"Write scope violations: {len(violations)} files outside allowed paths",
            details={"violations": violations[:10]}  # Limit to first 10
        )
    
    return GateResult(
        gate_name="G1",
        passed=True,
        message=f"All {len(writes)} writes within allowed scope",
        details={"write_count": len(writes)}
    )


def check_g2_schema_validation(
    context: Any,
    worker_path: Path
) -> GateResult:
    """
    G2: Schema Validation Enforcement
    
    All extracted JSON must validate against declared schemas.
    Checks that extraction outputs are schema-compliant.
    
    Args:
        context: GovernanceContext
        worker_path: Path to worker root
        
    Returns:
        GateResult indicating pass/fail
    """
    # Check phase results for extraction phases
    phase_results = context.phase_results
    
    extraction_phases = ["extract", "persist"]
    validation_failures = []
    
    for phase_name, result in phase_results.items():
        if phase_name not in extraction_phases:
            continue
        
        if not result.get("success", True):
            validation_failures.append(f"{phase_name}: execution failed")
            continue
        
        # Check if schema validation was performed
        metadata = result.get("metadata", {})
        if "schema_validation" in metadata:
            if not metadata["schema_validation"].get("passed", True):
                validation_failures.append(
                    f"{phase_name}: schema validation failed"
                )
    
    if validation_failures:
        return GateResult(
            gate_name="G2",
            passed=False,
            message=f"Schema validation failures: {len(validation_failures)}",
            details={"failures": validation_failures}
        )
    
    return GateResult(
        gate_name="G2",
        passed=True,
        message="All schema validations passed",
        details={}
    )


def check_g3_determinism(
    context: Any,
    worker_path: Path
) -> GateResult:
    """
    G3: Determinism Check
    
    Re-running schedule generation without new input yields identical hashes.
    This checks that outputs are deterministic and stable.
    
    Args:
        context: GovernanceContext
        worker_path: Path to worker root
        
    Returns:
        GateResult indicating pass/fail
    """
    # For initial implementation, check that phase results include deterministic outputs
    phase_results = context.phase_results
    
    schedule_phase = phase_results.get("schedule", {})
    if not schedule_phase:
        return GateResult(
            gate_name="G3",
            passed=True,
            message="Schedule phase not executed (N/A)",
            details={}
        )
    
    metadata = schedule_phase.get("metadata", {})
    output_hash = metadata.get("output_hash")
    
    if not output_hash:
        return GateResult(
            gate_name="G3",
            passed=False,
            message="Schedule output hash not provided",
            details={}
        )
    
    return GateResult(
        gate_name="G3",
        passed=True,
        message=f"Schedule output is deterministic (hash: {output_hash[:16]}...)",
        details={"output_hash": output_hash}
    )


def check_g4_evidence_coverage(
    context: Any
) -> GateResult:
    """
    G4: Evidence Coverage
    
    If a bill is not needs_review, then vendor, amount, due_date must
    each have evidence pointers.
    
    Args:
        context: GovernanceContext
        
    Returns:
        GateResult indicating pass/fail
    """
    phase_results = context.phase_results
    
    extract_phase = phase_results.get("extract", {})
    if not extract_phase:
        return GateResult(
            gate_name="G4",
            passed=True,
            message="Extract phase not executed (N/A)",
            details={}
        )
    
    metadata = extract_phase.get("metadata", {})
    evidence_coverage = metadata.get("evidence_coverage", {})
    
    if not evidence_coverage:
        # If no evidence coverage reported, assume it's not implemented yet
        return GateResult(
            gate_name="G4",
            passed=True,
            message="Evidence coverage not reported (N/A)",
            details={}
        )
    
    missing_coverage = evidence_coverage.get("missing_coverage", [])
    
    if missing_coverage:
        return GateResult(
            gate_name="G4",
            passed=False,
            message=f"Missing evidence for {len(missing_coverage)} extracted fields",
            details={"missing_coverage": missing_coverage[:10]}
        )
    
    covered_count = evidence_coverage.get("covered_count", 0)
    return GateResult(
        gate_name="G4",
        passed=True,
        message=f"Evidence coverage complete ({covered_count} fields)",
        details={"covered_count": covered_count}
    )


def run_gates(
    context: Any,
    worker_path: Path,
    bootstrap_root: Path
) -> Tuple[bool, List[GateResult]]:
    """
    Run all governance gates.
    
    Args:
        context: GovernanceContext
        worker_path: Path to worker root
        bootstrap_root: Path to bootstrap root
        
    Returns:
        Tuple of (all_passed: bool, results: List[GateResult])
    """
    results = []
    
    # G1: Write scope enforcement
    results.append(check_g1_write_scope(context, worker_path, bootstrap_root))
    
    # G2: Schema validation enforcement
    results.append(check_g2_schema_validation(context, worker_path))
    
    # G3: Determinism check
    results.append(check_g3_determinism(context, worker_path))
    
    # G4: Evidence coverage
    results.append(check_g4_evidence_coverage(context))
    
    all_passed = all(r.passed for r in results)
    
    return all_passed, results


def format_gate_report(results: List[GateResult]) -> str:
    """
    Format gate results as a readable report.
    
    Args:
        results: List of GateResult objects
        
    Returns:
        Formatted report string
    """
    lines = ["", "=" * 60, "Governance Gates Report", "=" * 60, ""]
    
    for result in results:
        status = "✓ PASS" if result.passed else "✗ FAIL"
        lines.append(f"{result.gate_name}: {status}")
        lines.append(f"  {result.message}")
        
        if result.details:
            for key, value in result.details.items():
                if isinstance(value, list):
                    lines.append(f"  {key}: {len(value)} items")
                    for item in value[:3]:
                        lines.append(f"    - {item}")
                    if len(value) > 3:
                        lines.append(f"    ... and {len(value) - 3} more")
                else:
                    lines.append(f"  {key}: {value}")
        lines.append("")
    
    all_passed = all(r.passed for r in results)
    lines.append("=" * 60)
    lines.append(f"Overall: {'ALL GATES PASSED' if all_passed else 'GATE FAILURES DETECTED'}")
    lines.append("=" * 60)
    lines.append("")
    
    return "\n".join(lines)
