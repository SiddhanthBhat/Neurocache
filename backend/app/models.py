# backend/app/models.py

from pydantic import BaseModel
from typing import List, Optional

class Project(BaseModel):
    id: str
    conference: str
    year: int
    link: str
    domain: str
    title: str
    summary: str
    tags: str
    date_added: str
    ready_to_publish: bool
    script: List[str]

class TTSRequest(BaseModel):
    script_text: str
    output_file: str
    male_voice: str
    female_voice: str
    random_pause_enabled: bool
    pause_min_sec: float
    pause_max_sec: float
    enable_gestures: bool
    gesture_prob: float
    gesture_phrases_csv: str
    enable_bg_music: bool
    bg_choice_name: Optional[str] = None
    bg_reduction_db: int
    add_bg_end: bool
    bg_end_duration_sec: int

class BatchTTSRequest(BaseModel):
    project_ids: List[str]
    # Include any TTS settings you want to apply to the whole batch
    male_voice: str
    female_voice: str