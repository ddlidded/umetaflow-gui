from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    workspaces_dir: Path


def get_repo_root() -> Path:
    # src/webapp/services.py -> repo root is 2 parents up: /workspace
    return Path(__file__).resolve().parents[2]


def load_settings(repo_root: Path) -> dict:
    import json

    settings_path = repo_root / "settings.json"
    with open(settings_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_paths() -> AppPaths:
    repo_root = get_repo_root()
    settings = load_settings(repo_root)
    # Use a writable location by default (inside the repo root).
    # The previous Streamlit implementation used a parent directory, which may not
    # be writable in some deployments (e.g., sandboxed environments).
    workspaces_dir = (repo_root / f"workspaces-{settings['repository-name']}").resolve()
    workspaces_dir.mkdir(parents=True, exist_ok=True)
    return AppPaths(repo_root=repo_root, workspaces_dir=workspaces_dir)


def new_workspace_id() -> str:
    return str(uuid.uuid4())


def get_workspace_dir(paths: AppPaths, workspace_id: str) -> Path:
    ws = (paths.workspaces_dir / workspace_id).resolve()
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "mzML-files").mkdir(parents=True, exist_ok=True)
    return ws


def list_mzml_files(workspace_dir: Path) -> list[str]:
    mzml_dir = workspace_dir / "mzML-files"
    if not mzml_dir.exists():
        return []
    return sorted([p.name for p in mzml_dir.iterdir() if p.is_file() and p.suffix.lower() == ".mzml"])


def update_mzml_df(df_path: Path, mzml_dir: Path) -> pd.DataFrame:
    """
    Mirror of the Streamlit helper, but headless (no Streamlit dependency).
    """
    if not df_path.exists():
        files = [f.name for f in mzml_dir.iterdir() if f.is_file()]
        df = pd.DataFrame({"file name": files, "use in workflows": [True] * len(files)})
    else:
        df = pd.read_csv(df_path, sep="\t")
        current_files = set(f.name for f in mzml_dir.iterdir() if f.is_file())
        df = df[df["file name"].isin(current_files)]
        existing_files = set(df["file name"])
        new_files = [
            f.name
            for f in mzml_dir.iterdir()
            if f.is_file() and f.suffix.lower() == ".mzml" and f.name not in existing_files
        ]
        if new_files:
            new_df = pd.DataFrame({"file name": new_files, "use in workflows": [True] * len(new_files)})
            df = pd.concat([df, new_df])
    return df.sort_values(by="file name").reset_index(drop=True)


def write_mzml_selection(df_path: Path, mzml_dir: Path, selected_files: Iterable[str]) -> None:
    files = [p.name for p in mzml_dir.iterdir() if p.is_file() and p.suffix.lower() == ".mzml"]
    selected_set = set(selected_files)
    df = pd.DataFrame(
        {"file name": sorted(files), "use in workflows": [f in selected_set for f in sorted(files)]}
    )
    df.to_csv(df_path, sep="\t", index=False)


def save_uploaded_files(workspace_dir: Path, uploads: Iterable[tuple[str, bytes]]) -> list[str]:
    """
    Save uploaded files into workspace/mzML-files.

    uploads: iterable of (filename, bytes)
    Returns list of saved file names.
    """
    mzml_dir = workspace_dir / "mzML-files"
    mzml_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for filename, content in uploads:
        if not filename.lower().endswith(".mzml"):
            continue
        out = mzml_dir / Path(filename).name
        out.write_bytes(content)
        saved.append(out.name)
    return saved


def workflow_dir_for(workspace_dir: Path, workflow_name: str = "UmetaFlow") -> Path:
    return workspace_dir / workflow_name.replace(" ", "-").lower()


def read_log_tail(workflow_dir: Path, log_name: str = "minimal.log", max_chars: int = 40_000) -> str:
    log_path = workflow_dir / "logs" / log_name
    if not log_path.exists():
        return ""
    data = log_path.read_text(encoding="utf-8", errors="replace")
    if len(data) <= max_chars:
        return data
    return data[-max_chars:]


def pid_file_paths(workflow_dir: Path) -> list[Path]:
    pid_dir = workflow_dir / "pids"
    if not pid_dir.exists():
        return []
    return sorted([p for p in pid_dir.iterdir() if p.is_file()])


def workflow_is_running(workflow_dir: Path) -> bool:
    return len(pid_file_paths(workflow_dir)) > 0

