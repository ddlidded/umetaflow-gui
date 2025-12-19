from __future__ import annotations

import csv
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    workspaces_dir: Path


def get_repo_root() -> Path:
    # In dev: src/webapp/services.py -> repo root is 2 parents up.
    # In PyInstaller: resources are unpacked into sys._MEIPASS.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass).resolve()
    return Path(__file__).resolve().parents[2]


def get_app_data_dir(app_name: str) -> Path:
    """
    Return a writable per-user app data directory.
    - macOS: ~/Library/Application Support/<app_name>
    - Linux: ~/.local/share/<app_name>
    - Windows: %APPDATA%\\<app_name> (best-effort)
    """
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / app_name
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / app_name
        return home / "AppData" / "Roaming" / app_name
    return home / ".local" / "share" / app_name


def load_settings(repo_root: Path) -> dict:
    import json

    settings_path = repo_root / "settings.json"
    with open(settings_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_paths() -> AppPaths:
    repo_root = get_repo_root()
    settings = load_settings(repo_root)
    # Use a writable location.
    # - Dev: inside repo root
    # - Packaged (PyInstaller): inside user app data (persistent across runs)
    if getattr(sys, "_MEIPASS", None):
        base = get_app_data_dir(settings.get("app-name", "UmetaFlow"))
        workspaces_dir = (base / f"workspaces-{settings['repository-name']}").resolve()
    else:
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


def _read_tsv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return list(reader)


def _write_tsv_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def update_mzml_df(df_path: Path, mzml_dir: Path) -> list[dict]:
    """
    Mirror of the Streamlit helper, but headless (no Streamlit dependency).
    """
    current_files = sorted([f.name for f in mzml_dir.iterdir() if f.is_file() and f.suffix.lower() == ".mzml"])

    existing_rows = _read_tsv_rows(df_path)
    existing_map: dict[str, bool] = {}
    for r in existing_rows:
        fn = r.get("file name", "")
        if not fn:
            continue
        existing_map[fn] = str(r.get("use in workflows", "True")).lower() in ("true", "1", "yes", "y", "on")

    rows: list[dict] = []
    for fn in current_files:
        rows.append({"file name": fn, "use in workflows": existing_map.get(fn, True)})

    rows.sort(key=lambda r: r["file name"])
    _write_tsv_rows(df_path, rows, fieldnames=["file name", "use in workflows"])
    return rows


def write_mzml_selection(df_path: Path, mzml_dir: Path, selected_files: Iterable[str]) -> None:
    files = [p.name for p in mzml_dir.iterdir() if p.is_file() and p.suffix.lower() == ".mzml"]
    selected_set = set(selected_files)
    rows = [
        {"file name": f, "use in workflows": (f in selected_set)}
        for f in sorted(files)
    ]
    _write_tsv_rows(df_path, rows, fieldnames=["file name", "use in workflows"])


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


def expert_flag_path(workspace_dir: Path) -> Path:
    return workspace_dir / "umetaflow-expert-flag.txt"


def is_expert_mode(workspace_dir: Path) -> bool:
    return expert_flag_path(workspace_dir).exists()


def read_simple_params(workspace_dir: Path) -> dict:
    import json
    params_path = workspace_dir / "umetaflow" / "params.json"
    defaults = {
        # Basic parameters
        "ion_mode": "positive",
        "mz_tolerance": 10.0,
        "RT_tolerance": 30.0,
        "num_threads": 1,
        
        # FeatureFinderMetabo parameters
        "ffm:algorithm:common:noise_threshold_int": 1000.0,
        "ffm:algorithm:common:chrom_peak_snr": 3.0,
        "ffm:algorithm:common:chrom_fwhm": 5.0,
        "ffm:algorithm:ffm:remove_single_traces": "true",
        
        # Adduct detection
        "adduct-detection": False,
        "adducts_pos": "H:+:0.6 Na:+:0.1 NH4:+:0.1 H-1O-1:+:0.1 H-3O-2:+:0.1",
        "adducts_neg": "H-1:-:1 H-2O-1:0:0.05 CH2O2:0:0.5",
        
        # Advanced parameters for expert mode
        "correct-precursor": True,
        "re-quantify": True,
        "run-ms2query": False,
        "run-sirius": False,
        "sirius-path": "",
        "generate-gnps": False,
        "generate-iimn": False,
        
        # MapAligner parameters
        "ma:algorithm:common:max_number_of_peaks_considered": 200000,
        "ma:algorithm:common:max_rt_shift": 30.0,
        "ma:algorithm:common:rt_tolerance": 30.0,
        
        # FeatureLinker parameters
        "fl:algorithm:common:rt_tolerance": 30.0,
        "fl:algorithm:common:mz_tolerance": 10.0,
        "fl:algorithm:common:mz_unit": "ppm",
        
        # MetaboliteAdductDecharger parameters
        "mad:algorithm:common:charge_min": 1,
        "mad:algorithm:common:charge_max": 3,
        "mad:algorithm:common:rt_tolerance": 30.0,
        "mad:algorithm:common:mz_tolerance": 10.0,
        "mad:algorithm:common:mz_unit": "ppm",
    }
    if params_path.exists():
        try:
            with open(params_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**defaults, **data}
        except Exception:
            return defaults.copy()
    return defaults.copy()


def write_simple_params(workspace_dir: Path, params: dict) -> None:
    import json
    path = workspace_dir / "umetaflow" / "params.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2)
