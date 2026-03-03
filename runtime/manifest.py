"""
Governance manifest generation.

Creates manifests and evidence records for worker execution.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    
    if not file_path.exists() or not file_path.is_file():
        return ""
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    
    return sha256.hexdigest()


def compute_string_hash(content: str) -> str:
    """Compute SHA256 hash of string content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def generate_manifest(
    context: Any,
    gate_results: List[Any],
    worker_config: Any
) -> Dict[str, Any]:
    """
    Generate governance manifest for a worker run.
    
    Args:
        context: GovernanceContext
        gate_results: List of GateResult objects
        worker_config: WorkerConfig object
        
    Returns:
        Manifest dictionary
    """
    # Collect output hashes
    outputs = []
    for write_path in context.actual_writes:
        path_obj = Path(write_path)
        if path_obj.exists():
            outputs.append({
                "path": str(write_path),
                "sha256": compute_file_hash(path_obj)
            })
    
    # Collect phase summaries
    phase_summaries = {}
    for phase_name, result in context.phase_results.items():
        phase_summaries[phase_name] = {
            "success": result.get("success", True),
            "metadata": result.get("metadata", {})
        }
    
    # Gate results summary
    gates_summary = {
        result.gate_name: {
            "passed": result.passed,
            "message": result.message,
            "details": result.details
        }
        for result in gate_results
    }
    
    # Collect counts from phase results
    emails_scanned = 0
    candidates_count = 0
    attachments_downloaded_count = 0
    attachments_parsed_count = 0
    bills_extracted_count = 0
    bills_persisted_count = 0
    needs_review_count = 0
    errors_count = 0
    
    for phase_name, result in context.phase_results.items():
        metadata = result.get("metadata", {})
        
        if phase_name == "ingest":
            emails_scanned = metadata.get("emails_scanned", 0)
            attachments_downloaded_count = metadata.get("attachments_count", 0)
        elif phase_name == "classify":
            candidates_count = metadata.get("candidates_count", 0)
        elif phase_name == "parse_attachments":
            attachments_parsed_count = metadata.get("attachments_parsed", 0)
        elif phase_name == "extract":
            bills_extracted_count = metadata.get("bills_extracted", 0)
            needs_review_count = metadata.get("needs_review_count", 0)
        elif phase_name == "persist":
            bills_persisted_count = metadata.get("bills_persisted", 0)
        
        if not result.get("success", True):
            errors_count += 1
    
    manifest = {
        "run_id": context.run_id,
        "timestamp_utc": context.timestamp.isoformat(),
        "worker": {
            "name": worker_config.name,
            "description": worker_config.description,
            "path": str(worker_config.worker_path)
        },
        "execution": {
            "dry_run": context.dry_run,
            "parameters": context.parameters,
            "phases": list(context.phase_results.keys())
        },
        "statistics": {
            "emails_scanned": emails_scanned,
            "candidates_count": candidates_count,
            "attachments_downloaded_count": attachments_downloaded_count,
            "attachments_parsed_count": attachments_parsed_count,
            "bills_extracted_count": bills_extracted_count,
            "bills_persisted_count": bills_persisted_count,
            "needs_review_count": needs_review_count,
            "errors_count": errors_count
        },
        "governance": {
            "gates": gates_summary,
            "all_gates_passed": all(r.passed for r in gate_results),
            "evidence_items_count": len(context.evidence_items)
        },
        "outputs": outputs,
        "phases": phase_summaries
    }
    
    return manifest


def write_manifest(
    manifest: Dict[str, Any],
    manifest_path: Path
) -> None:
    """
    Write manifest to file.
    
    Args:
        manifest: Manifest dictionary
        manifest_path: Path to write manifest
    """
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def write_evidence(
    evidence_items: List[Dict[str, Any]],
    evidence_path: Path
) -> None:
    """
    Write evidence items to JSONL file.
    
    Args:
        evidence_items: List of evidence dictionaries
        evidence_path: Path to write evidence
    """
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(evidence_path, "w", encoding="utf-8") as f:
        for item in evidence_items:
            f.write(json.dumps(item) + "\n")


def create_governance_artifacts(
    context: Any,
    gate_results: List[Any],
    worker_config: Any
) -> None:
    """
    Create all governance artifacts (manifest, evidence).
    
    Args:
        context: GovernanceContext
        gate_results: List of GateResult objects
        worker_config: WorkerConfig object
    """
    # Generate manifest
    manifest = generate_manifest(context, gate_results, worker_config)
    
    # Write manifest
    write_manifest(manifest, context.run_manifest_path)
    
    # Write evidence
    evidence_path = context.evidence_dir / "evidence.jsonl"
    write_evidence(context.evidence_items, evidence_path)
    
    # Write gate report
    from .gates import format_gate_report
    gate_report = format_gate_report(gate_results)
    gate_report_path = context.governance_dir / "runs" / context.run_id / "gate_report.txt"
    gate_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(gate_report_path, "w", encoding="utf-8") as f:
        f.write(gate_report)
