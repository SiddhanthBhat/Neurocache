import os
import io
import csv
import uuid
import json
import shutil
from shutil import rmtree
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from starlette.responses import FileResponse

from fastapi import Body


# ---- Reuse your existing logic from app.py
# Make sure app.py is in the same folder and contains the previously shared functions.
from app import (
    GENERATED_FOLDER, PROJECTS_DIR, now_iso, safe_stem,
    gemini_extract_metadata_and_script, write_project_json,
    process_script, list_project_ids, load_script_from_meta
)

# ---------------- Config / Folders ----------------
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)


ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT, ".env"))


def ensure_project_dir(pid: str) -> str:
    pdir = os.path.join(PROJECTS_DIR, pid)
    os.makedirs(pdir, exist_ok=True)
    return pdir

def project_json_path(pid: str) -> str:
    return os.path.join(PROJECTS_DIR, pid, "project.json")

def papers_dir(pid: str) -> str:
    d = os.path.join(PROJECTS_DIR, pid, "papers")
    os.makedirs(d, exist_ok=True)
    return d

def paper_dir(pid: str, paper_id: str) -> str:
    d = os.path.join(papers_dir(pid), paper_id)
    os.makedirs(d, exist_ok=True)
    return d

def paper_json_path(pid: str, paper_id: str) -> str:
    return os.path.join(paper_dir(pid, paper_id), "paper.json")

def paper_pdf_path(pid: str, paper_id: str) -> str:
    # Keep original extension if we want; default to .pdf
    pj = paper_json_path(pid, paper_id)
    meta = {}
    try:
        with open(pj, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        pass
    fname = meta.get("filename", f"{paper_id}.pdf")
    return os.path.join(paper_dir(pid, paper_id), fname)

def paper_meta_path(pid: str, paper_id: str) -> str:
    # per-paper Gemini output
    return os.path.join(paper_dir(pid, paper_id), "meta.json")

def read_json(fp: str, default):
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def write_json(fp: str, data: dict):
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------------- FastAPI ----------------
app = FastAPI(title="Neurocache API", version="0.1.0")

# CORS for Next dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range"],  # for scrubbers; FileResponse handles range
)


# ---------- Projects ----------
@app.get("/api/projects")
def list_projects():
    out = []
    # Don't use list_project_ids() here. It only returns projects that have meta.json (legacy).
    for pid in os.listdir(PROJECTS_DIR):
        pdir = os.path.join(PROJECTS_DIR, pid)
        pj = project_json_path(pid)  # projects/{pid}/project.json
        if os.path.isdir(pdir) and os.path.exists(pj):
            out.append(read_json(pj, {}))
    # newest first
    out.sort(key=lambda x: x.get("updatedAt", x.get("createdAt", "")), reverse=True)
    return out



@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    pdir = os.path.join(PROJECTS_DIR, pid)
    if not os.path.isdir(pdir) or not os.path.exists(project_json_path(pid)):
        raise HTTPException(404, "project not found")
    try:
        rmtree(pdir)
    except Exception as e:
        raise HTTPException(500, f"failed to delete project: {e}")
    return {"status": "deleted", "id": pid}


@app.post("/api/projects")
def create_project(payload: Dict[str, Any]):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    desc = payload.get("description", "")
    pid = str(uuid.uuid4())
    ensure_project_dir(pid)
    pj = {
        "id": pid,
        "name": name,
        "description": desc,
        "tags": payload.get("tags", []),
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }
    write_json(project_json_path(pid), pj)
    return pj

@app.get("/api/projects/{pid}")
def get_project(pid: str):
    pj = project_json_path(pid)
    if not os.path.exists(pj):
        raise HTTPException(404, "project not found")
    return read_json(pj, {})

# ---------- Papers ----------
@app.post("/api/projects/{pid}/papers/upload")
def upload_paper(pid: str, file: UploadFile = File(...)):
    if not os.path.exists(project_json_path(pid)):
        raise HTTPException(404, "project not found")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    paper_id = str(uuid.uuid4())
    pdir = paper_dir(pid, paper_id)
    dest = os.path.join(pdir, safe_stem(file.filename) + ".pdf")

    with open(dest, "wb") as out:
        shutil.copyfileobj(file.file, out)

    meta = {
        "id": paper_id,
        "projectId": pid,
        "filename": os.path.basename(dest),
        "originalName": file.filename,
        "size": os.path.getsize(dest),
        "mime": "application/pdf",
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }
    write_json(paper_json_path(pid, paper_id), meta)

    # touch project updatedAt
    pj = read_json(project_json_path(pid), {})
    pj["updatedAt"] = now_iso()
    write_json(project_json_path(pid), pj)
    return meta

@app.get("/api/projects/{pid}/papers")
def list_papers(pid: str):
    if not os.path.exists(project_json_path(pid)):
        raise HTTPException(404, "project not found")
    out = []
    pdir = papers_dir(pid)
    for paper_id in os.listdir(pdir):
        pj = paper_json_path(pid, paper_id)
        if os.path.exists(pj):
            out.append(read_json(pj, {}))
    out.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    return out

@app.get("/api/projects/{pid}/papers/{paper_id}")
def get_paper(pid: str, paper_id: str):
    pj = paper_json_path(pid, paper_id)
    if not os.path.exists(pj):
        raise HTTPException(404, "paper not found")
    return read_json(pj, {})

@app.get("/api/projects/{pid}/papers/{paper_id}/file")
def get_paper_file(pid: str, paper_id: str):
    pdf = paper_pdf_path(pid, paper_id)
    if not os.path.exists(pdf):
        raise HTTPException(404, f"pdf not found at {pdf}")
    return FileResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{os.path.basename(pdf)}"'}
    )


# ---------- Tools: Summarize (Gemini) ----------
@app.post("/api/projects/{pid}/papers/tools/summarize")
def summarize_batch(pid: str, body: Dict[str, Any] = Body(...)):
    paper_ids: List[str] = body.get("paperIds", [])
    if not paper_ids:
        raise HTTPException(400, "paperIds required")
    results = []
    for paper_id in paper_ids:
        try:
            # reuse single summarize
            _ = summarize_paper(pid, paper_id)  # will raise if fails
            results.append({"paperId": paper_id, "status": "done"})
        except HTTPException as e:
            results.append({"paperId": paper_id, "status": "error", "detail": e.detail})
        except Exception as e:
            results.append({"paperId": paper_id, "status": "error", "detail": str(e)})
    return {"results": results}

@app.post("/api/projects/{pid}/papers/tools/podcast")
def podcast_batch(pid: str, body: Dict[str, Any] = Body(...)):
    paper_ids: List[str] = body.get("paperIds", [])
    if not paper_ids:
        raise HTTPException(400, "paperIds required")
    results = []
    for paper_id in paper_ids:
        try:
            _ = podcast_paper(pid, paper_id)  # reuses single path
            results.append({"paperId": paper_id, "status": "done"})
        except HTTPException as e:
            results.append({"paperId": paper_id, "status": "error", "detail": e.detail})
        except Exception as e:
            results.append({"paperId": paper_id, "status": "error", "detail": str(e)})
    return {"results": results}

@app.get("/api/projects/{pid}/summaries")
def list_project_summaries(pid: str):
    """Return papers in this project that have per-paper meta.json"""
    if not os.path.exists(project_json_path(pid)):
        raise HTTPException(404, "project not found")
    out = []
    base = papers_dir(pid)
    for paper_id in os.listdir(base):
        mp = paper_meta_path(pid, paper_id)
        pj = paper_json_path(pid, paper_id)
        if os.path.exists(mp) and os.path.exists(pj):
            meta = read_json(mp, {})
            paper = read_json(pj, {})
            out.append({
                "paperId": paper_id,
                "title": meta.get("title", paper.get("originalName", "Untitled")),
                "summary": meta.get("summary", ""),
                "conference": meta.get("conference", "Unknown"),
                "year": int(meta.get("year", datetime.now().year)),
                "domain": meta.get("domain", "Unknown"),
                "tags": meta.get("tags", ""),
                "pdfUrl": f"/api/projects/{pid}/papers/{paper_id}/file",
            })
    # newest-ish first (not perfect but good enough)
    out.sort(key=lambda r: r.get("title",""), reverse=False)
    return out

@app.get("/api/projects/{pid}/podcasts")
def list_project_podcasts(pid: str):
    """
    Return podcast rows for this project. We include:
      1) MP3s inside each paper folder (preferred)
      2) Any MP3s found in generated_podcasts/ (fallback)
    so the UI always has a playable URL.
    """
    if not os.path.exists(project_json_path(pid)):
        raise HTTPException(404, "project not found")

    out = []

    # 1) Per-paper mp3s
    base = papers_dir(pid)
    if os.path.isdir(base):
        for paper_id in os.listdir(base):
            pdir = paper_dir(pid, paper_id)
            if not os.path.isdir(pdir):
                continue
            mp3s = sorted(
                [fn for fn in os.listdir(pdir) if fn.lower().endswith(".mp3")],
                reverse=True
            )
            if mp3s:
                # Title
                title = None
                mp = paper_meta_path(pid, paper_id)
                pj = paper_json_path(pid, paper_id)
                if os.path.exists(mp):
                    title = read_json(mp, {}).get("title")
                if not title and os.path.exists(pj):
                    title = read_json(pj, {}).get("originalName")
                out.append({
                    "paperId": paper_id,
                    "title": title or mp3s[0],
                    "mp3Url": f"/api/projects/{pid}/papers/{paper_id}/podcasts/{mp3s[0]}",
                    "pdfUrl": f"/api/projects/{pid}/papers/{paper_id}/file",
                })

    # 2) Fallback: anything under generated_podcasts/
    try:
        gen = [fn for fn in os.listdir(GENERATED_FOLDER) if fn.lower().endswith(".mp3")]
    except FileNotFoundError:
        gen = []

    # Include these too so you can always play what you see in Explorer
    for fn in sorted(gen, reverse=True):
        out.append({
            "paperId": "unknown",
            "title": fn,
            "mp3Url": f"/api/podcasts/global/{fn}",
            "pdfUrl": "",
        })

    return out


@app.post("/api/projects/{pid}/papers/{paper_id}/tools/summarize")
def summarize_paper(pid: str, paper_id: str):
    pdf = paper_pdf_path(pid, paper_id)
    if not os.path.exists(pdf):
        raise HTTPException(404, "pdf not found")
    try:
        data = gemini_extract_metadata_and_script(pdf)
    except Exception as e:
        raise HTTPException(500, f"Gemini failed: {e}")

    # Persist per-paper meta.json for table view
    write_json(paper_meta_path(pid, paper_id), data)

    # Also reflect core fields into top-level project index (optional)
    # (You already have project-level meta in your Gradio flow.)
    return {"status": "done", "metadata": data}

@app.get("/api/projects/{pid}/papers/{paper_id}/metadata")
def get_paper_metadata(pid: str, paper_id: str):
    mp = paper_meta_path(pid, paper_id)
    if not os.path.exists(mp):
        raise HTTPException(404, "metadata not found; run summarize")
    data = read_json(mp, {})
    # Normalize for frontend’s MetadataRow shape
    row = {
        "paperId": paper_id,
        "conference": data.get("conference", "Unknown"),
        "year": int(data.get("year", datetime.now().year)),
        "link": data.get("link", "Unknown"),
        "domain": data.get("domain", "Unknown"),
        "title": data.get("title", "Unknown Title"),
        "summary": data.get("summary", ""),
        "tags": data.get("tags", ""),
        "date_added": now_iso(),
        "ready_to_publish": bool(data.get("ready_to_publish", False)),
        "script_lines": len(data.get("script", [])) if isinstance(data.get("script", []), list) else 0,
    }
    return row

# ---------- Tools: Podcast (Kokoro) ----------
@app.post("/api/projects/{pid}/papers/{paper_id}/tools/podcast")
def podcast_paper(pid: str, paper_id: str):
    mp = paper_meta_path(pid, paper_id)
    if not os.path.exists(mp):
        raise HTTPException(400, "No metadata/script. Run summarize first.")
    data = read_json(mp, {})
    script_lines = data.get("script", [])
    if not script_lines or not isinstance(script_lines, list):
        raise HTTPException(400, "No script in metadata")

    script_text = "\n".join(script_lines)

    # defaults; adjust as you like
    model_path = "./models/kokoro-v1.0.onnx"
    voice_config = "voices-v1.0.bin"
    male_voice = "am_adam"
    female_voice = "af_heart"

    project_name = read_json(project_json_path(pid), {}).get("name", pid)
    file_base = f"{safe_stem(project_name)}_{paper_id}.mp3"

    audio_path, file_path, md = process_script(
        script_text=script_text,
        output_file=file_base,
        model_path=model_path,
        voice_config_path=voice_config,
        male_voice=male_voice,
        female_voice=female_voice,
        random_pause_enabled=True,
        pause_min_sec=0.2,
        pause_max_sec=0.4,
        enable_gestures=False,
        gesture_prob=0.2,
        gesture_phrases_csv="yeah, uh-huh, right, ok",
        enable_bg_music=False,
        bg_choice_name=None,
        bg_map={},
        bg_reduction_db=20,
        add_bg_end=False,
        bg_end_duration_sec=3,
        kokoro=None,
        progress=None,
    )

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(500, "podcast generation failed")

    # Try to copy into paper folder for per-paper serving; fall back to global serving
    paper_out = os.path.join(paper_dir(pid, paper_id), os.path.basename(file_path))
    mp3_url = None
    try:
        shutil.copy2(file_path, paper_out)
        mp3_url = f"/api/projects/{pid}/papers/{paper_id}/podcasts/{os.path.basename(file_path)}"
    except Exception:
        # fallback: serve directly from generated_podcasts
        mp3_url = f"/api/podcasts/global/{os.path.basename(file_path)}"

    return {"status": "done", "mp3Url": mp3_url, "message": md}


@app.get("/api/projects/{pid}/papers/{paper_id}/podcasts")
def list_podcasts(pid: str, paper_id: str):
    d = paper_dir(pid, paper_id)
    files = []
    for fn in sorted(os.listdir(d), reverse=True):
        if fn.lower().endswith(".mp3"):
            files.append({
                "id": safe_stem(fn),
                "paperId": paper_id,
                "mp3Url": f"/api/projects/{pid}/papers/{paper_id}/podcasts/{fn}",
                "durationSec": 0.0,  # could parse from file if needed
                "createdAt": now_iso(),
            })
    return files

@app.get("/api/projects/{pid}/papers/{paper_id}/podcasts/{name}")
def get_podcast_file(pid: str, paper_id: str, name: str):
    path = os.path.join(paper_dir(pid, paper_id), name)
    if not os.path.exists(path):
        alt = os.path.join(GENERATED_FOLDER, name)
        if not os.path.exists(alt):
            raise HTTPException(404, "mp3 not found")
        path = alt

    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-store",
        "Content-Disposition": f'inline; filename="{os.path.basename(path)}"',
    }
    return FileResponse(path, media_type="audio/mpeg", headers=headers)

@app.get("/api/debug/generated")
def debug_generated():
    import os
    from app import GENERATED_FOLDER
    folder_abs = os.path.abspath(GENERATED_FOLDER)
    listing = []
    if os.path.isdir(GENERATED_FOLDER):
        for fn in os.listdir(GENERATED_FOLDER):
            fp = os.path.join(GENERATED_FOLDER, fn)
            listing.append({
                "name": fn,
                "size": os.path.getsize(fp) if os.path.isfile(fp) else None,
            })
    return {
        "cwd": os.getcwd(),
        "generated_abs": folder_abs,
        "generated_exists": os.path.isdir(GENERATED_FOLDER),
        "files": listing,
    }


# Global fallback for MP3s sitting in generated_podcasts/
@app.get("/api/podcasts/global/{name:path}")
def get_global_podcast(name: str):
    # Normalize: strip leading slashes
    name = name.lstrip("/\\")
    base = os.path.abspath(GENERATED_FOLDER)
    if not os.path.isdir(base):
        raise HTTPException(404, f"generated_podcasts missing at {base}")

    # 1) Exact match
    candidate = os.path.join(base, name)
    if os.path.isfile(candidate):
        headers = {
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{os.path.basename(candidate)}"',
        }
        return FileResponse(candidate, media_type="audio/mpeg", headers=headers)

    # 2) Case-insensitive fallback (Windows sometimes hides true casing)
    lower = name.lower()
    for fn in os.listdir(base):
        if fn.lower() == lower:
            candidate = os.path.join(base, fn)
            headers = {
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-store",
                "Content-Disposition": f'inline; filename="{fn}"',
            }
            return FileResponse(candidate, media_type="audio/mpeg", headers=headers)

    # 3) Not found: return helpful info
    available = [f for f in os.listdir(base) if f.lower().endswith(".mp3")]
    raise HTTPException(
        404,
        detail={
            "message": f"mp3 not found in {base}",
            "requested": name,
            "available_count": len(available),
            "example": available[0] if available else None,
        },
    )



# ---------- Project table ----------
@app.get("/api/projects/{pid}/metadata/table")
def table_rows(pid: str):
    rows = []
    pdir = papers_dir(pid)
    for paper_id in os.listdir(pdir):
        mp = paper_meta_path(pid, paper_id)
        if os.path.exists(mp):
            data = read_json(mp, {})
            rows.append({
                "paperId": paper_id,
                "conference": data.get("conference", "Unknown"),
                "year": int(data.get("year", datetime.now().year)),
                "link": data.get("link", "Unknown"),
                "domain": data.get("domain", "Unknown"),
                "title": data.get("title", "Unknown Title"),
                "summary": data.get("summary", ""),
                "tags": data.get("tags", ""),
                "date_added": now_iso(),
                "ready_to_publish": bool(data.get("ready_to_publish", False)),
                "script_lines": len(data.get("script", [])) if isinstance(data.get("script", []), list) else 0,
            })
    return rows

@app.get("/api/projects/{pid}/metadata/csv")
def table_csv(pid: str):
    rows = table_rows(pid)
    if not rows:
        raise HTTPException(404, "no rows")
    # Stream CSV
    def gen():
        out = io.StringIO()
        fields = list(rows[0].keys())
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        yield out.getvalue()
    return StreamingResponse(gen(), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename=project_{pid}_metadata.csv"})
