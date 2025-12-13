from __future__ import annotations

import traceback
import shutil
import subprocess
import sys
from pathlib import Path
from multiprocessing import Process


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
    )
    out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
    return p.returncode, out.strip()


def _log_to_workflow(workflow_dir: Path, message: str) -> None:
    (workflow_dir / "logs").mkdir(parents=True, exist_ok=True)
    for log_name in ("minimal.log", "commands-and-run-times.log", "all.log"):
        try:
            with open(workflow_dir / "logs" / log_name, "a", encoding="utf-8") as f:
                f.write(message + "\n\n")
        except Exception:
            pass


def ensure_processing_dependencies(workspace_dir: Path) -> None:
    """
    Best-effort auto-install for missing processing dependencies.

    - Tries Python deps via pip (pyopenms, rdkit, etc.)
    - Tries OpenMS command line tools via conda/mamba/micromamba if available
    """
    wf_dir = workspace_dir / "umetaflow"

    def pip_install(pkgs: list[str]) -> None:
        cmd = [sys.executable, "-m", "pip", "install", "--no-cache-dir", *pkgs]
        rc, out = _run(cmd)
        _log_to_workflow(wf_dir, f"[deps] pip {' '.join(pkgs)}\n{out}")
        if rc != 0:
            raise RuntimeError(f"pip install failed for: {pkgs}")

    def have_import(mod: str) -> bool:
        try:
            __import__(mod)
            return True
        except Exception:
            return False

    def which(exe: str) -> bool:
        import shutil as _sh

        return _sh.which(exe) is not None

    _log_to_workflow(wf_dir, "[deps] Checking processing dependencies…")

    # Python packages (best-effort; compiled wheels may not exist for this Python/OS)
    if not have_import("pyopenms"):
        _log_to_workflow(wf_dir, "[deps] Missing: pyopenms. Attempting install…")
        pip_install(["pyopenms==3.2"])

    # rdkit is used by parts of the pipeline (optional depending on features used)
    if not have_import("rdkit"):
        _log_to_workflow(wf_dir, "[deps] Missing: rdkit. Attempting install…")
        pip_install(["rdkit==2023.9.4"])

    if not have_import("ms2query"):
        _log_to_workflow(wf_dir, "[deps] Missing: ms2query. Attempting install…")
        pip_install(["ms2query==1.5.3"])

    if not have_import("sklearn"):
        _log_to_workflow(wf_dir, "[deps] Missing: scikit-learn. Attempting install…")
        pip_install(["scikit-learn"])

    # OpenMS CLI tools (required). Try conda-family installers if available.
    if not which("FeatureFinderMetabo"):
        _log_to_workflow(
            wf_dir,
            "[deps] Missing: OpenMS command-line tools (e.g. FeatureFinderMetabo). Attempting install via conda/mamba…",
        )
        installer = None
        for candidate in ("micromamba", "mamba", "conda"):
            if which(candidate):
                installer = candidate
                break

        if installer:
            # Install OpenMS from bioconda/conda-forge into the current environment if possible.
            # This may fail depending on how Python is installed; we log output either way.
            cmd = [
                installer,
                "install",
                "-y",
                "-c",
                "conda-forge",
                "-c",
                "bioconda",
                "openms=3.2",
            ]
            rc, out = _run(cmd, cwd=workspace_dir)
            _log_to_workflow(wf_dir, f"[deps] {installer} install openms=3.2\n{out}")
            if rc != 0:
                raise RuntimeError("Failed to install OpenMS tools via conda/mamba.")
        else:
            raise RuntimeError(
                "OpenMS tools are missing and no conda/mamba/micromamba is available for auto-install."
            )


def _run_umetaflow(workspace_dir: str) -> None:
    """
    Target function for background process (must be top-level for multiprocessing).
    """
    wf_dir = Path(workspace_dir) / "umetaflow"
    try:
        ensure_processing_dependencies(Path(workspace_dir))
        from src.UmetaFlowTOPPWorkflow import Workflow
        wf = Workflow(workspace_dir, enable_ui=False)
        wf.workflow_process()
    except Exception:
        # Best-effort logging (works even if Workflow couldn't be imported)
        (wf_dir / "logs").mkdir(parents=True, exist_ok=True)
        msg = "ERROR: Failed to start/run UmetaFlow (headless).\n\n" + traceback.format_exc()
        _log_to_workflow(wf_dir, msg)
    finally:
        # Ensure the "running" indicator is cleared even on early import failures.
        shutil.rmtree(wf_dir / "pids", ignore_errors=True)


def start_umetaflow(workspace_dir: Path) -> int:
    """
    Start the UmetaFlow workflow in a background process.
    Returns the workflow PID.
    """
    # mimic Streamlit behavior: clear logs before starting
    workflow_dir = workspace_dir / "umetaflow"
    shutil.rmtree(workflow_dir / "logs", ignore_errors=True)
    shutil.rmtree(workflow_dir / "pids", ignore_errors=True)
    (workflow_dir / "pids").mkdir(parents=True, exist_ok=True)

    p = Process(target=_run_umetaflow, args=(str(workspace_dir),))
    p.start()
    # store pid marker (same scheme as Streamlit UI)
    (workflow_dir / "pids" / str(p.pid)).touch()
    return int(p.pid)

