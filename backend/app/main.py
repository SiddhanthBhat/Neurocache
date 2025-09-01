# backend/app/main.py

import os
import shutil
import uuid
from typing import List
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask

from . import core
from .models import Project, TTSRequest, BatchTTSRequest

app = FastAPI()

BG_MUSIC_MAP = {}
BG_MUSIC_FOLDER = "bg_music"
os.makedirs(BG_MUSIC_FOLDER, exist_ok=True)

# Configure CORS
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/projects/", response_model=List[Project])
async def list_projects():
    """Lists all projects by reading their meta.json files."""
    projects = []
    for project_id in core.list_project_ids():
        meta_path = os.path.join(core.PROJECTS_DIR, project_id, "meta.json")
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                projects.append(data)
        except Exception:
            continue
    return projects

@app.post("/api/bg-music/")
async def upload_bg_music(file: UploadFile = File(...)):
    """Uploads a background music file."""
    file_path = os.path.join(BG_MUSIC_FOLDER, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update our in-memory map
    BG_MUSIC_MAP[file.filename] = file_path
    return {"filename": file.filename, "path": file_path}

@app.get("/api/bg-music/")
async def get_bg_music_list():
    """Returns a list of available background music filenames."""
    return list(BG_MUSIC_MAP.keys())

# ... (keep the /api/tts/ POST endpoint, but update it to use the BG_MUSIC_MAP)

@app.post("/api/tts/")
async def create_tts(request: TTSRequest):
    try:
        audio_path, _, _ = core.process_script(
            script_text=request.script_text,
            output_file=request.output_file,
            # ... other params
            bg_map=BG_MUSIC_MAP, # Pass the map here
            # ... rest of params
        )
        return {"file_path": audio_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/batch-tts/")
async def batch_create_tts(request: BatchTTSRequest):
    """Generates podcasts for a batch of projects and returns a ZIP file."""
    core.clear_generated_folder()
    generated_files = []
    
    for pid in request.project_ids:
        script_lines = core.load_script_from_meta(pid)
        if not script_lines:
            continue

        script_text = "\n".join(script_lines)
        out_file = core.default_output_name_for_pid(pid)
        
        try:
            audio_path, _, _ = core.process_script(
                script_text=script_text,
                output_file=out_file,
                model_path=core.MODEL_OPTIONS[0],
                voice_config_path="voices-v1.0.bin",
                male_voice=request.male_voice,
                female_voice=request.female_voice,
                # Using default values for simplicity in batch mode
                random_pause_enabled=True,
                pause_min_sec=0.2,
                pause_max_sec=0.8,
                enable_gestures=False,
                gesture_prob=0,
                gesture_phrases_csv="",
                enable_bg_music=False,
                bg_choice_name=None,
                bg_map=BG_MUSIC_MAP,
                bg_reduction_db=20,
                add_bg_end=False,
                bg_end_duration_sec=3,
            )
            generated_files.append(audio_path)
        except Exception as e:
            # You might want to log this error
            print(f"Failed to process {pid}: {e}")
            continue

    if not generated_files:
        raise HTTPException(status_code=400, detail="No podcasts were generated.")

    zip_name = f"podcasts_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path = core.zip_files(generated_files, zip_name)
    
    # Use BackgroundTask to clean up the ZIP file after sending it
    cleanup_task = BackgroundTask(os.remove, zip_path)
    return FileResponse(zip_path, media_type="application/zip", filename=zip_name, background=cleanup_task)

@app.post("/api/projects/", response_model=Project)
async def create_project(file: UploadFile = File(...)):
    project_id = str(uuid.uuid4())
    project_dir = os.path.join(core.PROJECTS_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)
    pdf_path = os.path.join(project_dir, file.filename)

    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        data = core.gemini_extract_metadata_and_script(pdf_path)
        data["id"] = project_id
        core.write_project_json(project_id, data)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tts/")
async def create_tts(request: TTSRequest):
    try:
        audio_path, _, _ = core.process_script(
            script_text=request.script_text,
            output_file=request.output_file,
            model_path=core.MODEL_OPTIONS[0],  # Or make this configurable
            voice_config_path="voices-v1.0.bin",
            male_voice=request.male_voice,
            female_voice=request.female_voice,
            random_pause_enabled=request.random_pause_enabled,
            pause_min_sec=request.pause_min_sec,
            pause_max_sec=request.pause_max_sec,
            enable_gestures=request.enable_gestures,
            gesture_prob=request.gesture_prob,
            gesture_phrases_csv=request.gesture_phrases_csv,
            enable_bg_music=request.enable_bg_music,
            bg_choice_name=request.bg_choice_name,
            bg_map={},  # Handle background music uploads separately
            bg_reduction_db=request.bg_reduction_db,
            add_bg_end=request.add_bg_end,
            bg_end_duration_sec=request.bg_end_duration_sec,
        )
        return {"file_path": audio_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/podcasts/")
def get_podcasts():
    return core.mp3_choices()

@app.get("/api/podcasts/{podcast_name}")
def get_podcast(podcast_name: str):
    file_path = core.mp3_path_from_choice(podcast_name)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Podcast not found")