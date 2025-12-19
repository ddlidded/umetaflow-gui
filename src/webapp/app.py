from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.webapp.services import (
    get_paths,
    get_workspace_dir,
    list_mzml_files,
    new_workspace_id,
    read_log_tail,
    update_mzml_df,
    workflow_dir_for,
    workflow_is_running,
    write_mzml_selection,
    read_simple_params,
    write_simple_params,
    is_expert_mode,
    expert_flag_path,
)
from src.webapp.workflow_runner import start_umetaflow


app = FastAPI(title="UmetaFlow Web UI", version="1.0.0")

paths = get_paths()
templates = Jinja2Templates(directory=str(paths.repo_root / "src" / "webapp" / "templates"))

# Serve existing assets (logos, images)
app.mount("/assets", StaticFiles(directory=str(paths.repo_root / "assets")), name="assets")


def _workspace_id_from_request(request: Request) -> str:
    ws = request.cookies.get("workspace") or request.query_params.get("workspace")
    if not ws:
        ws = new_workspace_id()
    return ws


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    ws_id = _workspace_id_from_request(request)
    ws_dir = get_workspace_dir(paths, ws_id)
    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "workspace_id": ws_id,
            "mzml_count": len(list_mzml_files(ws_dir)),
        },
    )
    response.set_cookie("workspace", ws_id, httponly=False, samesite="lax")
    return response


@app.post("/workspace")
def set_workspace(request: Request, workspace: str = Form(default="")):
    ws_id = workspace.strip() or new_workspace_id()
    get_workspace_dir(paths, ws_id)
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie("workspace", ws_id, httponly=False, samesite="lax")
    return resp


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    ws_id = _workspace_id_from_request(request)
    ws_dir = get_workspace_dir(paths, ws_id)
    mzml_dir = ws_dir / "mzML-files"
    df_path = ws_dir / "mzML-files.tsv"
    files = update_mzml_df(df_path, mzml_dir)

    response = templates.TemplateResponse(
        "upload.html",
        {"request": request, "workspace_id": ws_id, "files": files},
    )
    response.set_cookie("workspace", ws_id, httponly=False, samesite="lax")
    return response


@app.post("/api/upload/mzml")
async def upload_mzml(request: Request, files: list[UploadFile] = File(default=[])):
    ws_id = _workspace_id_from_request(request)
    ws_dir = get_workspace_dir(paths, ws_id)
    mzml_dir = ws_dir / "mzML-files"
    mzml_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    for f in files:
        if not f.filename or not f.filename.lower().endswith(".mzml"):
            continue
        out = mzml_dir / Path(f.filename).name
        try:
            import shutil
            with out.open("wb") as dst:
                shutil.copyfileobj(f.file, dst, length=1024 * 1024)
        finally:
            await f.close()
        saved += 1

    # update selection table
    df_path = ws_dir / "mzML-files.tsv"
    update_mzml_df(df_path, mzml_dir)

    return JSONResponse({"ok": True, "saved": saved})


@app.post("/api/mzml/selection")
async def update_selection(request: Request):
    form = await request.form()
    selected = form.getlist("use_files")
    ws_id = _workspace_id_from_request(request)
    ws_dir = get_workspace_dir(paths, ws_id)
    write_mzml_selection(ws_dir / "mzML-files.tsv", ws_dir / "mzML-files", selected)
    return RedirectResponse(url="/upload", status_code=303)


@app.get("/run", response_class=HTMLResponse)
def run_page(request: Request):
    ws_id = _workspace_id_from_request(request)
    ws_dir = get_workspace_dir(paths, ws_id)
    wf_dir = workflow_dir_for(ws_dir, "UmetaFlow")
    running = workflow_is_running(wf_dir)
    log_text = read_log_tail(wf_dir, "minimal.log")
    response = templates.TemplateResponse(
        "run.html",
        {
            "request": request,
            "workspace_id": ws_id,
            "running": running,
            "log_text": log_text,
        },
    )
    response.set_cookie("workspace", ws_id, httponly=False, samesite="lax")
    return response


@app.post("/api/workflow/start")
def start_workflow(request: Request):
    ws_id = _workspace_id_from_request(request)
    ws_dir = get_workspace_dir(paths, ws_id)
    wf_dir = workflow_dir_for(ws_dir, "UmetaFlow")
    if workflow_is_running(wf_dir):
        return JSONResponse({"ok": True, "running": True, "message": "Already running."})
    pid = start_umetaflow(ws_dir)
    return JSONResponse({"ok": True, "running": True, "pid": pid})


@app.get("/api/workflow/status")
def workflow_status(request: Request):
    ws_id = _workspace_id_from_request(request)
    ws_dir = get_workspace_dir(paths, ws_id)
    wf_dir = workflow_dir_for(ws_dir, "UmetaFlow")
    return JSONResponse(
        {
            "running": workflow_is_running(wf_dir),
            "log": read_log_tail(wf_dir, "minimal.log"),
        }
    )


@app.get("/configure", response_class=HTMLResponse)
def configure_page(request: Request):
    ws_id = _workspace_id_from_request(request)
    ws_dir = get_workspace_dir(paths, ws_id)
    params = read_simple_params(ws_dir)
    response = templates.TemplateResponse(
        "configure.html",
        {
            "request": request,
            "workspace_id": ws_id,
            "params": params,
            "expert_mode": is_expert_mode(ws_dir),
        },
    )
    response.set_cookie("workspace", ws_id, httponly=False, samesite="lax")
    return response


@app.post("/api/settings/save")
async def save_settings(request: Request):
    form = await request.form()
    ws_id = _workspace_id_from_request(request)
    ws_dir = get_workspace_dir(paths, ws_id)
    expert = bool(form.get("expert_mode"))
    if expert:
        expert_flag_path(ws_dir).touch()
    else:
        expert_flag_path(ws_dir).unlink(missing_ok=True)
    
    def _get_num(name: str, default: float) -> float:
        try:
            return float(form.get(name, default))
        except Exception:
            return default
    
    def _get_bool(name: str, default: bool = False) -> bool:
        return form.get(name, "") == "on"
    
    params = {
        # Basic parameters
        "ion_mode": form.get("ion_mode", "positive"),
        "mz_tolerance": _get_num("mz_tolerance", 10.0),
        "RT_tolerance": _get_num("RT_tolerance", 30.0),
        "num_threads": int(_get_num("num_threads", 1)),
        
        # FeatureFinderMetabo parameters
        "ffm:algorithm:common:noise_threshold_int": _get_num("ffm_noise_threshold_int", 1000.0),
        "ffm:algorithm:common:chrom_peak_snr": _get_num("ffm_chrom_peak_snr", 3.0),
        "ffm:algorithm:common:chrom_fwhm": _get_num("ffm_chrom_fwhm", 5.0),
        "ffm:algorithm:ffm:remove_single_traces": form.get("ffm_remove_single_traces", "true"),
        
        # Adduct detection
        "adduct-detection": _get_bool("adduct_detection"),
        "adducts_pos": form.get("adducts_pos", ""),
        "adducts_neg": form.get("adducts_neg", ""),
        
        # Advanced parameters
        "correct-precursor": _get_bool("correct_precursor"),
        "re-quantify": _get_bool("re_quantify"),
        "run-ms2query": _get_bool("run_ms2query"),
        "run-sirius": _get_bool("run_sirius"),
        "sirius-path": form.get("sirius_path", ""),
        "generate-gnps": _get_bool("generate_gnps"),
        "generate-iimn": _get_bool("generate_iimn"),
        
        # MapAligner parameters
        "ma:algorithm:common:max_number_of_peaks_considered": _get_num("ma_max_peaks", 200000),
        "ma:algorithm:common:max_rt_shift": _get_num("ma_max_rt_shift", 30.0),
        "ma:algorithm:common:rt_tolerance": _get_num("ma_rt_tolerance", 30.0),
        
        # FeatureLinker parameters
        "fl:algorithm:common:rt_tolerance": _get_num("fl_rt_tolerance", 30.0),
        "fl:algorithm:common:mz_tolerance": _get_num("fl_mz_tolerance", 10.0),
        "fl:algorithm:common:mz_unit": form.get("fl_mz_unit", "ppm"),
        
        # MetaboliteAdductDecharger parameters
        "mad:algorithm:common:charge_min": int(_get_num("mad_charge_min", 1)),
        "mad:algorithm:common:charge_max": int(_get_num("mad_charge_max", 3)),
        "mad:algorithm:common:rt_tolerance": _get_num("mad_rt_tolerance", 30.0),
        "mad:algorithm:common:mz_tolerance": _get_num("mad_mz_tolerance", 10.0),
        "mad:algorithm:common:mz_unit": form.get("mad_mz_unit", "ppm"),
    }
    write_simple_params(ws_dir, params)
    return RedirectResponse(url="/configure", status_code=303)


@app.get("/results", response_class=HTMLResponse)
def results_page(request: Request):
    ws_id = _workspace_id_from_request(request)
    ws_dir = get_workspace_dir(paths, ws_id)
    wf_dir = workflow_dir_for(ws_dir)
    
    # Check if results exist
    results_exist = (wf_dir / "results").exists() if wf_dir else False
    
    # Mock data for demonstration - in real implementation, this would come from actual results
    summary = {
        "total_features": 1250,
        "annotated_features": 342,
        "ms2_matches": 89,
        "sirius_annotations": 56
    }
    
    recent_features = [
        {"id": "F001", "mz": 118.0863, "rt": 2.45, "intensity": 12500.34, "annotation": "Leucine"},
        {"id": "F002", "mz": 132.1019, "rt": 3.12, "intensity": 8900.67, "annotation": "Isoleucine"},
        {"id": "F003", "mz": 146.1176, "rt": 4.78, "intensity": 15600.89, "annotation": ""},
        {"id": "F004", "mz": 174.1117, "rt": 5.23, "intensity": 11200.45, "annotation": "Phenylalanine"},
        {"id": "F005", "mz": 204.1234, "rt": 6.89, "intensity": 9800.12, "annotation": ""}
    ]
    
    response = templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "workspace_id": ws_id,
            "results_exist": results_exist,
            "summary": summary,
            "recent_features": recent_features
        },
    )
    response.set_cookie("workspace", ws_id, httponly=False, samesite="lax")
    return response


@app.get("/statistics", response_class=HTMLResponse)
def statistics_page(request: Request):
    ws_id = _workspace_id_from_request(request)
    ws_dir = get_workspace_dir(paths, ws_id)
    wf_dir = workflow_dir_for(ws_dir)
    
    # Check if results exist
    results_exist = (wf_dir / "results").exists() if wf_dir else False
    
    # Mock data for demonstration - in real implementation, this would come from actual results
    stats = {
        "total_features": 1250,
        "annotated_features": 342,
        "ms2_matches": 89,
        "sirius_annotations": 56,
        "sirius_formulas": 42,
        "csi_annotations": 31,
        "canopus_annotations": 28,
        "ms2query_matches": 67,
        "adduct_groups": 23,
        "avg_cv": 15.2,
        "missing_values": 8.7,
        "rsd": 12.4,
        "snr": 25.8
    }
    
    response = templates.TemplateResponse(
        "statistics.html",
        {
            "request": request,
            "workspace_id": ws_id,
            "results_exist": results_exist,
            "stats": stats
        },
    )
    response.set_cookie("workspace", ws_id, httponly=False, samesite="lax")
    return response
