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
        out.write_bytes(await f.read())
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

