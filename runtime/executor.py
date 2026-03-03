"""
Bootstrap executor for governed workers.

Main execution orchestration that:
1. Loads worker configuration
2. Creates governance context
3. Executes phases sequentially
4. Runs governance gates
5. Produces manifest and evidence
"""

from pathlib import Path
from typing import Optional, List
import sys
import io

# Ensure UTF-8 encoding for output on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from .worker_loader import load_worker, WorkerConfig
from .governance_context import create_context, GovernanceContext, to_worker_runtime_context
from .gates import run_gates, format_gate_report, GateResult
from .manifest import create_governance_artifacts
from .paths import get_onedrive_roots, redact_path


class ExecutionError(Exception):
    """Raised when execution fails."""
    pass


class BootstrapExecutor:
    """Main executor for governed worker runs."""
    
    def __init__(self, bootstrap_root: Path):
        self.bootstrap_root = Path(bootstrap_root)
        
    def execute_worker(
        self,
        worker_name: str,
        dry_run: bool = False,
        since_weeks: Optional[int] = None,
        phases: Optional[List[str]] = None,
        write_artifacts: bool = True,
        **kwargs
    ) -> GovernanceContext:
        """
        Execute a worker with governance.
        
        Args:
            worker_name: Name of worker to execute
            dry_run: Whether to run in dry-run mode
            since_weeks: Number of weeks to look back (worker-specific)
            phases: List of phases to execute (None = all)
            **kwargs: Additional parameters for worker
            
        Returns:
            GovernanceContext with execution results
            
        Raises:
            ExecutionError: If execution or gates fail
        """
        onedrive_roots = get_onedrive_roots()
        try:
            home_dir = Path.home().resolve()
        except Exception:
            home_dir = None

        def _p(p: Path) -> str:
            return redact_path(p, home_dir=home_dir, onedrive_roots=onedrive_roots)

        print(f"\n{'='*60}")
        print(f"Bootstrap Execution: {worker_name}")
        print(f"{'='*60}")
        print(f"Mode: {'DRY-RUN' if dry_run else 'REAL RUN'}")
        if since_weeks:
            print(f"Since: {since_weeks} weeks")
        print()
        
        # Load worker
        print(f"[1/6] Loading worker configuration...")
        try:
            worker = load_worker(worker_name, self.bootstrap_root)
        except Exception as e:
            raise ExecutionError(f"Failed to load worker: {e}") from e
        
        print(f"  Worker: {worker.name}")
        print(f"  Description: {worker.description}")
        print(f"  Location: {_p(worker.worker_path)}")
        print(f"  Phases: {', '.join(worker.phases)}")
        print()
        
        # Create governance context
        print(f"[2/6] Creating governance context...")
        context = create_context(
            worker_name=worker.name,
            worker_path=worker.worker_path,
            bootstrap_root=self.bootstrap_root,
            dry_run=dry_run,
            since_weeks=since_weeks,
            **kwargs
        )
        print(f"  Run ID: {context.run_id}")
        print(f"  Governance dir: {_p(context.governance_dir)}")
        print()

        worker_context = to_worker_runtime_context(context)
        
        # Load worker adapter
        print(f"[3/6] Loading worker adapter...")
        try:
            worker.load_adapter()
        except Exception as e:
            raise ExecutionError(f"Failed to load adapter: {e}") from e
        
        print(f"  Adapter module: {worker.adapter_module_name}")
        print()
        
        # Execute phases
        print(f"[4/6] Executing phases...")
        phases_to_run = phases if phases else worker.phases
        
        for i, phase_name in enumerate(phases_to_run, 1):
            print(f"  Phase {i}/{len(phases_to_run)}: {phase_name}")
            
            try:
                result = worker.run_phase(phase_name, worker_context)
                context.record_phase_result(phase_name, result)
                
                # Record writes
                outputs = result.get("outputs", [])
                for output in outputs:
                    if context.dry_run:
                        context.record_planned_write(output)
                    else:
                        context.record_actual_write(output)
                
                # Record evidence
                evidence = result.get("evidence", [])
                for item in evidence:
                    context.record_evidence(item)
                
                success = result.get("success", True)
                status = "[OK]" if success else "[FAIL]"
                print(f"    {status} {result.get('message', 'Complete')}")
                
            except Exception as e:
                print(f"    [FAIL] Failed: {e}")
                context.record_phase_result(phase_name, {
                    "success": False,
                    "error": str(e),
                    "message": f"Phase failed: {e}"
                })
                # Continue to next phase or stop?
                # For now, continue but mark as error
        
        print()
        
        # Run governance gates
        print(f"[5/6] Running governance gates...")
        all_passed, gate_results = run_gates(
            context,
            worker.worker_path,
            self.bootstrap_root
        )
        
        for result in gate_results:
            status = "[OK]" if result.passed else "[FAIL]"
            print(f"  {status} {result.gate_name}: {result.message}")
        
        print()
        
        # Create governance artifacts
        if write_artifacts:
            print(f"[6/6] Creating governance artifacts...")
            try:
                create_governance_artifacts(context, gate_results, worker)
                print(f"  [OK] Manifest: {_p(context.run_manifest_path)}")
                print(f"  [OK] Evidence: {_p(context.evidence_dir / 'evidence.jsonl')}")
            except Exception as e:
                print(f"  [FAIL] Failed to create artifacts: {e}")
                raise ExecutionError(f"Failed to create governance artifacts: {e}") from e
        else:
            print(f"[6/6] Governance artifacts: SKIPPED (no-write mode)")
        
        print()
        
        # Report final status
        print(f"{'='*60}")
        if all_passed:
            print("[SUCCESS] Execution complete - ALL GATES PASSED")
        else:
            print("[FAILED] Execution complete - GATE FAILURES DETECTED")
        print(f"{'='*60}")
        print()
        
        if not all_passed:
            print(format_gate_report(gate_results))
            raise ExecutionError("Governance gates failed")
        
        return context


def execute_worker(
    worker_name: str,
    bootstrap_root: Optional[Path] = None,
    dry_run: bool = False,
    since_weeks: Optional[int] = None,
    phases: Optional[List[str]] = None,
    write_artifacts: bool = True,
    **kwargs
) -> GovernanceContext:
    """
    Convenience function to execute a worker.
    
    Args:
        worker_name: Name of worker to execute
        bootstrap_root: Path to bootstrap root (defaults to current directory)
        dry_run: Whether to run in dry-run mode
        since_weeks: Number of weeks to look back
        phases: List of phases to execute (None = all)
        **kwargs: Additional parameters for worker
        
    Returns:
        GovernanceContext with execution results
    """
    if bootstrap_root is None:
        bootstrap_root = Path.cwd()
    
    executor = BootstrapExecutor(bootstrap_root)
    return executor.execute_worker(
        worker_name=worker_name,
        dry_run=dry_run,
        since_weeks=since_weeks,
        phases=phases,
        write_artifacts=write_artifacts,
        **kwargs
    )
