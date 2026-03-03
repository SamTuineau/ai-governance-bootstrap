"""
Bootstrap CLI for governed worker execution.

Command-line interface for running workers under bootstrap governance.
"""

import argparse
import os
import sys
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path

from .executor import execute_worker, ExecutionError
from .worker_loader import WorkerRegistry
from .paths import (
    get_onedrive_roots,
    is_under_any_root,
    redact_path,
    resolve_bootstrap_governance_dir,
    resolve_worker_runtime_dir,
)


def _make_path_redactor():
    onedrive_roots = get_onedrive_roots()
    try:
        home_dir = Path.home().resolve()
    except Exception:
        home_dir = None

    def _p(path_obj: Path) -> str:
        return redact_path(Path(path_obj), home_dir=home_dir, onedrive_roots=onedrive_roots)

    return _p


def find_bootstrap_root() -> Path:
    """
    Find the bootstrap root directory.
    
    Looks for governance-version.json to identify bootstrap root.
    """
    # Prefer the installed package location (works regardless of CWD)
    module_root = Path(__file__).resolve().parents[1]
    if (module_root / "governance-version.json").exists():
        return module_root

    current = Path.cwd().resolve()
    
    # Check current directory
    if (current / "governance-version.json").exists():
        return current
    
    # Check parent directories
    for parent in current.parents:
        if (parent / "governance-version.json").exists():
            return parent
    
    # Default to current directory
    return current


def cmd_run(args):
    """Execute run command."""
    bootstrap_root = args.bootstrap_root or find_bootstrap_root()

    _p = _make_path_redactor()
    
    try:
        context = execute_worker(
            worker_name=args.worker,
            bootstrap_root=bootstrap_root,
            dry_run=args.dry_run,
            since_weeks=args.since_weeks,
        )
        
        print(f"\n[OK] Run ID: {context.run_id}")
        print(f"[OK] Manifest: {_p(context.run_manifest_path)}")
        
        return 0
        
    except ExecutionError as e:
        print(f"\n✗ Execution failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


def cmd_list(args):
    """Execute list command."""
    bootstrap_root = args.bootstrap_root or find_bootstrap_root()

    _p = _make_path_redactor()
    
    registry = WorkerRegistry(bootstrap_root)
    workers = registry.discover_workers()
    
    if not workers:
        print("No workers registered.")
        return 0
    
    print(f"\nRegistered Workers ({len(workers)}):")
    print("=" * 60)
    
    for name, worker in workers.items():
        print(f"\n{name}")
        print(f"  Description: {worker.description}")
        print(f"  Location: {_p(worker.worker_path)}")
        print(f"  Phases: {', '.join(worker.phases)}")
        print(f"  Dry-run supported: {'Yes' if worker.dry_run_supported else 'No'}")
    
    print()
    return 0


def cmd_info(args):
    """Execute info command."""
    bootstrap_root = args.bootstrap_root or find_bootstrap_root()

    _p = _make_path_redactor()
    
    registry = WorkerRegistry(bootstrap_root)
    worker = registry.get_worker(args.worker)
    
    if worker is None:
        print(f"✗ Worker '{args.worker}' not found.", file=sys.stderr)
        return 1
    
    print(f"\nWorker: {worker.name}")
    print("=" * 60)
    print(f"Description: {worker.description}")
    print(f"Location: {_p(worker.worker_path)}")
    print(f"Language: {worker.language}")
    print(f"Adapter module: {worker.adapter_module_name}")
    print(f"\nPhases:")
    for phase in worker.phases:
        print(f"  - {phase}")
    print(f"\nGovernance:")
    print(f"  Dry-run supported: {'Yes' if worker.dry_run_supported else 'No'}")
    print(f"  Evidence required: {'Yes' if worker.evidence_required else 'No'}")
    print(f"  Deterministic: {'Yes' if worker.deterministic else 'No'}")
    print()
    
    return 0


def main():
    """Main CLI entry point."""
    if sys.version_info[:2] != (3, 11):
        print("FAIL python_version: Python 3.11 required for deterministic runtime", file=sys.stderr)
        print(f"Detected: {sys.version.split()[0]} ({sys.executable})", file=sys.stderr)
        return 2

    parser = argparse.ArgumentParser(
        prog="run-bootstrap",
        description="Execute governed workers under bootstrap control"
    )
    
    parser.add_argument(
        "--bootstrap-root",
        type=Path,
        help="Path to bootstrap root (auto-detected if not specified)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # run command
    run_parser = subparsers.add_parser(
        "run",
        help="Execute a worker"
    )
    run_parser.add_argument(
        "--worker",
        required=True,
        help="Name of worker to execute"
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no writes)"
    )
    run_parser.add_argument(
        "--since-weeks",
        type=int,
        help="Number of weeks to look back (worker-specific)"
    )
    run_parser.set_defaults(func=cmd_run)
    
    # list command
    list_parser = subparsers.add_parser(
        "list",
        help="List registered workers"
    )
    list_parser.set_defaults(func=cmd_list)
    
    # info command
    info_parser = subparsers.add_parser(
        "info",
        help="Show worker information"
    )
    info_parser.add_argument(
        "--worker",
        required=True,
        help="Name of worker to show info for"
    )
    info_parser.set_defaults(func=cmd_info)

    # doctor command
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Check environment and path health (no auto-fix)"
    )
    doctor_parser.add_argument(
        "--worker",
        help="Optional worker name to validate (defaults to all discovered workers)"
    )
    doctor_parser.set_defaults(func=cmd_doctor)

    # selftest command
    selftest_parser = subparsers.add_parser(
        "selftest",
        help="Run deterministic safety harness (no writes)"
    )
    selftest_parser.add_argument(
        "--worker",
        help="Worker to self-test (defaults to the only discovered worker)"
    )
    selftest_parser.set_defaults(func=cmd_selftest)
    
    args = parser.parse_args()
    
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    
    return args.func(args)


def _check_writable_dir(path: Path) -> bool:
    """Best-effort directory writability check without leaving artifacts."""
    import tempfile

    try:
        path = Path(path).resolve()
        if not path.exists() or not path.is_dir():
            return False
        if os.access(str(path), os.W_OK) is False:
            # Still attempt tempfile; os.access can be misleading on Windows.
            pass
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(path), delete=True) as f:
            f.write(".")
        return True
    except Exception:
        return False


@contextmanager
def _temporary_env(overrides):
    """Temporarily set/unset environment variables for the duration of a block."""
    previous = {k: os.environ.get(k) for k in overrides.keys()}
    try:
        for key, value in overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def cmd_doctor(args):
    """Execute doctor command."""
    try:
        bootstrap_root = args.bootstrap_root or find_bootstrap_root()
        bootstrap_root = Path(bootstrap_root).resolve()

        onedrive_roots = get_onedrive_roots()
        home_dir = None
        try:
            home_dir = Path.home().resolve()
        except Exception:
            home_dir = None

        structural_failures = []
        warnings = []

        python_version = sys.version.split()[0]
        python_exe = sys.executable
        venv_path = Path(sys.prefix).resolve()
        venv_active = sys.prefix != getattr(sys, "base_prefix", sys.prefix)

        # Bootstrap root sanity
        version_file = bootstrap_root / "governance-version.json"
        if not version_file.exists():
            structural_failures.append("bootstrap_root_missing_governance_version.json")

        # Resolve configured roots
        governance_dir = resolve_bootstrap_governance_dir(bootstrap_root)

        # Validate governance dir (must exist + writable)
        if not governance_dir.exists():
            structural_failures.append("governance_dir_missing")
        elif not _check_writable_dir(governance_dir):
            structural_failures.append("governance_dir_not_writable")

        # OneDrive warnings (never fail)
        if onedrive_roots:
            for label, path_obj in (
                ("venv_path", venv_path),
                ("bootstrap_root", bootstrap_root),
                ("BOOTSTRAP_GOVERNANCE_DIR", governance_dir),
            ):
                if is_under_any_root(path_obj, onedrive_roots):
                    warnings.append(f"{label}_under_onedrive")

        # Workers
        registry = WorkerRegistry(bootstrap_root)
        discovered = registry.discover_workers()

        if args.worker:
            discovered = {args.worker: registry.get_worker(args.worker)}

        if not discovered:
            structural_failures.append("no_workers_discovered")

        per_worker_rows = []
        for name, worker in discovered.items():
            if worker is None:
                structural_failures.append(f"worker_not_found:{name}")
                continue

            worker_path = worker.worker_path
            if not worker_path.exists():
                structural_failures.append(f"worker_path_missing:{name}")

            runtime_dir = resolve_worker_runtime_dir(worker_path)
            # runtime dir must exist + writable (if env var points to something invalid, fail)
            if not runtime_dir.exists():
                structural_failures.append(f"worker_runtime_dir_missing:{name}")
            elif not _check_writable_dir(runtime_dir):
                structural_failures.append(f"worker_runtime_dir_not_writable:{name}")

            if onedrive_roots:
                if is_under_any_root(worker_path, onedrive_roots):
                    warnings.append(f"worker_path_under_onedrive:{name}")
                if is_under_any_root(runtime_dir, onedrive_roots):
                    warnings.append(f"WORKER_RUNTIME_DIR_under_onedrive:{name}")

            per_worker_rows.append((name, worker_path, runtime_dir))

        # Output report
        print("\nDoctor Report")
        print("=" * 60)

        print(f"Python version: {python_version}")
        print(f"Python executable: {redact_path(Path(python_exe), home_dir=home_dir, onedrive_roots=onedrive_roots)}")
        print(f"Venv active: {'Yes' if venv_active else 'No'}")
        print(f"Venv path: {redact_path(venv_path, home_dir=home_dir, onedrive_roots=onedrive_roots)}")
        print(f"Bootstrap root: {redact_path(bootstrap_root, home_dir=home_dir, onedrive_roots=onedrive_roots)}")

        raw_gov = os.getenv("BOOTSTRAP_GOVERNANCE_DIR")
        raw_worker_rt = os.getenv("WORKER_RUNTIME_DIR")
        print(
            "BOOTSTRAP_GOVERNANCE_DIR (raw): "
            + (raw_gov if (raw_gov and raw_gov.strip()) else "<unset>")
        )
        print(
            "BOOTSTRAP_GOVERNANCE_DIR (resolved): "
            + redact_path(governance_dir, home_dir=home_dir, onedrive_roots=onedrive_roots)
        )
        print(
            "WORKER_RUNTIME_DIR (raw): "
            + (raw_worker_rt if (raw_worker_rt and raw_worker_rt.strip()) else "<unset>")
        )
        print("WORKER_RUNTIME_DIR (resolved): <per-worker>")

        if onedrive_roots:
            roots_display = ", ".join(
                sorted(
                    {
                        redact_path(r, home_dir=home_dir, onedrive_roots=onedrive_roots)
                        for r in onedrive_roots
                    }
                )
            )
            print(f"OneDrive roots detected: {roots_display}")
        else:
            print("OneDrive roots detected: <none>")

        if per_worker_rows:
            print("\nWorkers")
            print("-" * 60)
            for name, worker_path, runtime_dir in per_worker_rows:
                print(f"{name}:")
                print(f"  Worker resolved path: {redact_path(worker_path, home_dir=home_dir, onedrive_roots=onedrive_roots)}")
                print(f"  WORKER_RUNTIME_DIR (resolved): {redact_path(runtime_dir, home_dir=home_dir, onedrive_roots=onedrive_roots)}")

        print("\nResults")
        print("-" * 60)
        if structural_failures:
            print("FAIL Structural errors detected:")
            for item in structural_failures:
                print(f"  - {item}")
            if warnings:
                print("WARN OneDrive warnings (non-fatal):")
                for item in sorted(set(warnings)):
                    print(f"  - {item}")
            print("\nNo auto-fix performed.")
            return 1

        if warnings:
            print("WARN OneDrive warnings detected (configuration still valid):")
            for item in sorted(set(warnings)):
                print(f"  - {item}")
            print("\nPASS Doctor checks passed (with warnings).")
            return 0

        print("PASS Doctor checks passed.")
        return 0

    except Exception as e:
        print("\nDoctor Report")
        print("=" * 60)
        print("FAIL Doctor crashed-safe (unexpected exception)")
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


def cmd_selftest(args):
    """Execute selftest command (deterministic safety harness; no writes)."""
    bootstrap_root = args.bootstrap_root or find_bootstrap_root()
    bootstrap_root = Path(bootstrap_root).resolve()

    registry = WorkerRegistry(bootstrap_root)
    discovered = registry.discover_workers()
    worker_name = args.worker

    if not worker_name:
        if len(discovered) == 1:
            worker_name = next(iter(discovered.keys()))
        else:
            available = ", ".join(sorted(discovered.keys()))
            print("SELFTEST FAIL")
            print("No worker specified and multiple workers discovered.")
            print(f"Available workers: {available}")
            return 1

    # Choose an isolated runtime/governance location that we DO NOT create.
    # Dry-run mode + write_artifacts=False ensures no external writes.
    unique = uuid.uuid4().hex
    temp_base = Path(tempfile.gettempdir()).resolve()
    isolated_runtime = (temp_base / "ai-governance-bootstrap" / "selftest" / unique).resolve()
    isolated_governance = (temp_base / "ai-governance-bootstrap" / "selftest-governance" / unique).resolve()

    def _run_once():
        context = execute_worker(
            worker_name=worker_name,
            bootstrap_root=bootstrap_root,
            dry_run=True,
            phases=["ingest", "schedule"],
            write_artifacts=False,
        )
        schedule_phase = context.phase_results.get("schedule") or {}
        metadata = schedule_phase.get("metadata") or {}
        return {
            "schedule_hash": metadata.get("schedule_hash") or metadata.get("output_hash"),
            "ledger_hash": metadata.get("ledger_hash"),
        }

    print("\nSelftest")
    print("=" * 60)
    print(f"Worker: {worker_name}")
    print(f"Mode: DRY-RUN (no writes)")
    onedrive_roots = get_onedrive_roots()
    try:
        home_dir = Path.home().resolve()
    except Exception:
        home_dir = None
    print(
        "WORKER_RUNTIME_DIR: "
        + redact_path(isolated_runtime, home_dir=home_dir, onedrive_roots=onedrive_roots)
    )
    print(
        "BOOTSTRAP_GOVERNANCE_DIR: "
        + redact_path(isolated_governance, home_dir=home_dir, onedrive_roots=onedrive_roots)
    )

    try:
        with _temporary_env({
            "WORKER_RUNTIME_DIR": str(isolated_runtime),
            "BOOTSTRAP_GOVERNANCE_DIR": str(isolated_governance),
        }):
            r1 = _run_once()
            r2 = _run_once()

        missing = [k for k in ("schedule_hash", "ledger_hash") if not (r1.get(k) and r2.get(k))]
        if missing:
            print("SELFTEST FAIL")
            print(f"Missing required hashes: {', '.join(missing)}")
            print(f"Run1: {r1}")
            print(f"Run2: {r2}")
            return 1

        ok = (r1["schedule_hash"] == r2["schedule_hash"]) and (r1["ledger_hash"] == r2["ledger_hash"])

        if ok:
            print("SELFTEST PASS")
            print(f"schedule_hash: {r1['schedule_hash']}")
            print(f"ledger_hash:   {r1['ledger_hash']}")
            return 0

        print("SELFTEST FAIL")
        print(f"Run1 schedule_hash: {r1['schedule_hash']}")
        print(f"Run2 schedule_hash: {r2['schedule_hash']}")
        print(f"Run1 ledger_hash:   {r1['ledger_hash']}")
        print(f"Run2 ledger_hash:   {r2['ledger_hash']}")
        return 1

    except ExecutionError as e:
        print("SELFTEST FAIL")
        print(f"ExecutionError: {e}")
        return 1
    except Exception as e:
        print("SELFTEST FAIL")
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
