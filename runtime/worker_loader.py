"""Worker loader for ai-governance-bootstrap.

Discovers and loads external worker configurations from workers/ directory.

Machine-agnostic path rules:
- worker.yaml `location.path` must be relative (no absolute paths)
- relative paths are resolved relative to the bootstrap repo root
- resolved paths must stay within the parent of the bootstrap repo root
    (intended to allow sibling repos like ../gmail-bills)
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
import importlib
import importlib.util


class WorkerConfig:
    """Represents a loaded worker configuration."""
    
    def __init__(self, config_path: Path, config_data: Dict[str, Any], bootstrap_root: Path):
        self.config_path = config_path
        self.data = config_data
        self.bootstrap_root = Path(bootstrap_root).resolve()
        self._adapter_module = None
        self._resolved_worker_path: Optional[Path] = None
        
    @property
    def name(self) -> str:
        return self.data["worker"]["name"]
    
    @property
    def description(self) -> str:
        return self.data["worker"]["description"]
    
    @property
    def worker_path(self) -> Path:
        if self._resolved_worker_path is None:
            self._resolved_worker_path = resolve_worker_path(
                worker_config=self.data,
                bootstrap_root=self.bootstrap_root,
                config_path=self.config_path,
            )
        return self._resolved_worker_path
    
    @property
    def adapter_module_name(self) -> str:
        return self.data["execution"]["adapter_module"]
    
    @property
    def language(self) -> str:
        return self.data["execution"]["language"]
    
    @property
    def phases(self) -> List[str]:
        return self.data["phases"]
    
    @property
    def governance_config(self) -> Dict[str, Any]:
        return self.data.get("governance", {})
    
    @property
    def dry_run_supported(self) -> bool:
        return self.governance_config.get("dry_run_supported", False)
    
    @property
    def evidence_required(self) -> bool:
        return self.governance_config.get("evidence_required", True)
    
    @property
    def deterministic(self) -> bool:
        return self.governance_config.get("deterministic", False)
    
    def load_adapter(self):
        """
        Dynamically load the worker's adapter module.
        
        Adds worker path to sys.path and imports the adapter module.
        Returns the imported module.
        """
        if self._adapter_module is not None:
            return self._adapter_module
        
        if self.language != "python":
            raise ValueError(
                f"Unsupported worker language: {self.language}. "
                "Only Python workers are currently supported."
            )
        
        # Insert worker path into sys.path if not already present
        worker_path_str = str(self.worker_path)
        if worker_path_str not in sys.path:
            sys.path.insert(0, worker_path_str)
        
        # Import the adapter module
        try:
            self._adapter_module = importlib.import_module(self.adapter_module_name)
        except ImportError as e:
            raise ImportError(
                f"Failed to import adapter module '{self.adapter_module_name}' "
                f"from worker at {self.worker_path}: {e}"
            ) from e
        
        # Verify adapter has required interface
        if not hasattr(self._adapter_module, "run_phase"):
            raise AttributeError(
                f"Adapter module '{self.adapter_module_name}' must "
                "implement 'run_phase(phase_name, context)' function"
            )
        
        return self._adapter_module
    
    def run_phase(self, phase_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a phase through the worker's adapter.
        
        Args:
            phase_name: Name of phase to execute
            context: Governance context
            
        Returns:
            Phase execution result
        """
        adapter = self.load_adapter()
        return adapter.run_phase(phase_name, context)


class WorkerRegistry:
    """Registry of available workers."""
    
    def __init__(self, bootstrap_root: Path):
        self.bootstrap_root = bootstrap_root
        self.workers_dir = bootstrap_root / "workers"
        self._workers: Dict[str, WorkerConfig] = {}
        
    def discover_workers(self) -> Dict[str, WorkerConfig]:
        """
        Discover all workers in the workers/ directory.
        
        Returns:
            Dict mapping worker names to WorkerConfig objects
        """
        if not self.workers_dir.exists():
            return {}
        
        self._workers = {}
        
        # Find all worker.yaml files
        for worker_dir in self.workers_dir.iterdir():
            if not worker_dir.is_dir():
                continue
            
            config_file = worker_dir / "worker.yaml"
            if not config_file.exists():
                continue
            
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)
                
                worker_config = WorkerConfig(config_file, config_data, bootstrap_root=self.bootstrap_root)
                self._workers[worker_config.name] = worker_config
                
            except Exception as e:
                print(f"Warning: Failed to load worker from {config_file}: {e}")
                continue
        
        return self._workers
    
    def get_worker(self, name: str) -> Optional[WorkerConfig]:
        """Get a worker by name."""
        if not self._workers:
            self.discover_workers()
        return self._workers.get(name)
    
    def list_workers(self) -> List[str]:
        """List all available worker names."""
        if not self._workers:
            self.discover_workers()
        return list(self._workers.keys())


def load_worker(worker_name: str, bootstrap_root: Path) -> WorkerConfig:
    """
    Load a worker configuration by name.
    
    Args:
        worker_name: Name of the worker to load
        bootstrap_root: Path to bootstrap repository root
        
    Returns:
        WorkerConfig object
        
    Raises:
        ValueError: If worker not found
    """
    registry = WorkerRegistry(bootstrap_root)
    registry.discover_workers()
    
    worker = registry.get_worker(worker_name)
    if worker is None:
        available = ", ".join(registry.list_workers())
        raise ValueError(
            f"Worker '{worker_name}' not found. "
            f"Available workers: {available}"
        )
    
    return worker


def resolve_worker_path(worker_config: Dict[str, Any], bootstrap_root: Path, config_path: Path) -> Path:
    """Resolve and validate a worker root path from worker.yaml.

    Rules:
    - Reject absolute paths (machine/user specific)
    - Resolve relative paths from bootstrap_root
    - Ensure resolved path stays within the parent of bootstrap_root
      (allows sibling repos such as ../gmail-bills)
    """
    location = worker_config.get("location") or {}
    raw_path = location.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError(f"Invalid worker location.path in {config_path}: must be a non-empty string")

    raw_path = raw_path.strip()
    path_obj = Path(raw_path)
    if path_obj.is_absolute():
        raise ValueError(
            "Worker location.path must be relative (absolute paths are not allowed). "
            f"Found: {raw_path!r} in {config_path}"
        )

    bootstrap_root = Path(bootstrap_root).resolve()
    allowed_root = bootstrap_root.parent.resolve()
    resolved = (bootstrap_root / path_obj).resolve()

    # Prevent escaping the intended workspace root
    try:
        if not resolved.is_relative_to(allowed_root):
            raise ValueError(
                "Resolved worker path escapes the allowed workspace root. "
                f"Resolved: {str(resolved)!r} Allowed root: {str(allowed_root)!r} "
                f"(from {config_path})"
            )
    except AttributeError:
        # Path.is_relative_to exists on Python 3.9+. This project enforces 3.11,
        # but keep a safe fallback.
        resolved_parts = resolved.parts
        allowed_parts = allowed_root.parts
        if resolved_parts[: len(allowed_parts)] != allowed_parts:
            raise ValueError(
                "Resolved worker path escapes the allowed workspace root. "
                f"Resolved: {str(resolved)!r} Allowed root: {str(allowed_root)!r} "
                f"(from {config_path})"
            )

    return resolved
