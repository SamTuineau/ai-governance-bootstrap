"""
Governance context for worker execution.

Provides the execution context that workers receive, including:
- Run identification
- Dry-run flag
- Paths (data, governance)
- Runtime parameters
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

from .paths import resolve_bootstrap_governance_dir, resolve_worker_runtime_dir


class GovernanceContext:
    """
    Execution context provided to workers.
    
    This context is passed to each phase and contains all runtime
    configuration and governance parameters.
    """
    
    def __init__(
        self,
        run_id: str,
        worker_name: str,
        worker_path: Path,
        bootstrap_root: Path,
        dry_run: bool = False,
        parameters: Optional[Dict[str, Any]] = None
    ):
        self.run_id = run_id
        self.worker_name = worker_name
        self.worker_path = Path(worker_path)
        self.bootstrap_root = Path(bootstrap_root).resolve()
        self.dry_run = dry_run
        self.parameters = parameters or {}
        self.timestamp = datetime.now(timezone.utc)

        self._governance_base_dir = resolve_bootstrap_governance_dir(self.bootstrap_root)
        self._worker_runtime_dir = resolve_worker_runtime_dir(self.worker_path)
        
        # Initialize tracking
        self._planned_writes: List[str] = []
        self._actual_writes: List[str] = []
        self._evidence_items: List[Dict[str, Any]] = []
        self._phase_results: Dict[str, Dict[str, Any]] = {}
        
        # Shared state for data passing between phases
        self.state: Dict[str, Any] = {}
        
    @property
    def governance_dir(self) -> Path:
        """Bootstrap governance directory."""
        return self._governance_base_dir

    @property
    def worker_runtime_dir(self) -> Path:
        """Resolved worker runtime directory (WORKER_RUNTIME_DIR or worker root)."""
        return self._worker_runtime_dir

    def resolve_worker_path(self, *parts: str, scope: str = "runtime") -> Path:
        """Resolve a worker-related path using the shared resolver.

        Args:
            *parts: Path segments under the selected root
            scope: "runtime" (default) or "worker"

        Returns:
            Resolved Path
        """
        if scope not in ("runtime", "worker"):
            raise ValueError("scope must be 'runtime' or 'worker'")

        root = self.worker_runtime_dir if scope == "runtime" else self.worker_path
        if not parts:
            return Path(root).resolve()
        return Path(root, *parts).resolve()
    
    @property
    def evidence_dir(self) -> Path:
        """Evidence directory for this run."""
        return self.governance_dir / "evidence" / self.run_id
    
    @property
    def run_manifest_path(self) -> Path:
        """Run manifest file path."""
        return self.governance_dir / "runs" / self.run_id / "manifest.json"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary for passing to workers.
        
        Workers receive this context and can access:
        - run_id
        - dry_run
        - worker_path (where worker can write data)
        - governance_dir (where bootstrap writes governance artifacts)
        - state (shared mutable dict for passing data between phases)
        - Any custom parameters
        """
        return {
            "run_id": self.run_id,
            "worker_name": self.worker_name,
            "worker_path": str(self.worker_path),
            "bootstrap_root": str(self.bootstrap_root),
            "governance_dir": str(self.governance_dir),
            "bootstrap_governance_dir": str(self.governance_dir),
            "evidence_dir": str(self.evidence_dir),
            "worker_runtime_dir": str(self.worker_runtime_dir),
            "dry_run": self.dry_run,
            "timestamp_utc": self.timestamp.isoformat(),
            "state": self.state,  # Shared mutable state
            **self.parameters
        }
    
    def record_planned_write(self, path: str):
        """Record a planned write (dry-run mode)."""
        self._planned_writes.append(path)
    
    def record_actual_write(self, path: str):
        """Record an actual write."""
        self._actual_writes.append(path)
    
    def record_evidence(self, evidence_item: Dict[str, Any]):
        """Record an evidence item."""
        self._evidence_items.append(evidence_item)
    
    def record_phase_result(self, phase_name: str, result: Dict[str, Any]):
        """Record a phase execution result."""
        self._phase_results[phase_name] = result
    
    @property
    def planned_writes(self) -> List[str]:
        """Get all planned writes."""
        return self._planned_writes.copy()
    
    @property
    def actual_writes(self) -> List[str]:
        """Get all actual writes."""
        return self._actual_writes.copy()
    
    @property
    def evidence_items(self) -> List[Dict[str, Any]]:
        """Get all evidence items."""
        return self._evidence_items.copy()
    
    @property
    def phase_results(self) -> Dict[str, Dict[str, Any]]:
        """Get all phase results."""
        return self._phase_results.copy()


def create_context(
    worker_name: str,
    worker_path: Path,
    bootstrap_root: Path,
    dry_run: bool = False,
    since_weeks: Optional[int] = None,
    **kwargs
) -> GovernanceContext:
    """
    Create a new governance context for worker execution.
    
    Args:
        worker_name: Name of the worker
        worker_path: Path to worker root
        bootstrap_root: Path to bootstrap root
        dry_run: Whether this is a dry-run
        since_weeks: Number of weeks to look back (worker-specific)
        **kwargs: Additional parameters to pass to worker
        
    Returns:
        GovernanceContext instance
    """
    run_id = f"{worker_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    parameters = kwargs.copy()
    if since_weeks is not None:
        parameters["since_weeks"] = since_weeks
    
    return GovernanceContext(
        run_id=run_id,
        worker_name=worker_name,
        worker_path=worker_path,
        bootstrap_root=bootstrap_root,
        dry_run=dry_run,
        parameters=parameters
    )


class WorkerRuntimeContext(dict):
    """Dict-like payload passed into worker phases.

    Behaves like a normal dict for existing workers, but also provides a
    shared resolver via `context.resolve_worker_path(...)`.
    """

    def __init__(self, base: Dict[str, Any], *, worker_runtime_dir: Path, worker_root: Path):
        super().__init__(base)
        self._worker_runtime_dir = Path(worker_runtime_dir).resolve()
        self._worker_root = Path(worker_root).resolve()

    @property
    def worker_runtime_dir(self) -> Path:
        return self._worker_runtime_dir

    @property
    def worker_root(self) -> Path:
        return self._worker_root

    def resolve_worker_path(self, *parts: str, scope: str = "runtime") -> Path:
        if scope not in ("runtime", "worker"):
            raise ValueError("scope must be 'runtime' or 'worker'")

        root = self.worker_runtime_dir if scope == "runtime" else self.worker_root
        if not parts:
            return Path(root).resolve()
        return Path(root, *parts).resolve()


def to_worker_runtime_context(context: GovernanceContext) -> WorkerRuntimeContext:
    """Create a WorkerRuntimeContext from a GovernanceContext."""
    base = context.to_dict()
    return WorkerRuntimeContext(
        base,
        worker_runtime_dir=context.worker_runtime_dir,
        worker_root=context.worker_path,
    )
