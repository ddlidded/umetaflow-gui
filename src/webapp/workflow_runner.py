from __future__ import annotations

import traceback
import shutil
from pathlib import Path
from multiprocessing import Process


def _run_umetaflow(workspace_dir: str) -> None:
    """
    Target function for background process (must be top-level for multiprocessing).
    """
    wf_dir = Path(workspace_dir) / "umetaflow"
    try:
        from src.UmetaFlowTOPPWorkflow import Workflow
        wf = Workflow(workspace_dir, enable_ui=False)
        wf.workflow_process()
    except Exception:
        # Best-effort logging (works even if Workflow couldn't be imported)
        (wf_dir / "logs").mkdir(parents=True, exist_ok=True)
        msg = "ERROR: Failed to start/run UmetaFlow (headless).\n\n" + traceback.format_exc()
        for log_name in ("minimal.log", "commands-and-run-times.log", "all.log"):
            try:
                (wf_dir / "logs" / log_name).write_text(msg, encoding="utf-8")
            except Exception:
                pass
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

