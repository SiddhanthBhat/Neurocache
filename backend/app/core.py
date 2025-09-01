# app.py
import os
import re
import csv
import json
import time
import uuid
import zipfile
import random
import shutil
from datetime import datetime
from typing import Dict, Any, List, Tuple

import numpy as np
import gradio as gr
from pydub import AudioSegment
from pypdf import PdfReader
from dotenv import load_dotenv

# ---------- TTS ----------
from kokoro_onnx import Kokoro

# ---------- Gemini ----------
import google.generativeai as genai

# =========================================================
# Config / Paths
# =========================================================
load_dotenv()

GENERATED_FOLDER = "generated_podcasts"
PROJECTS_DIR = "projects"
os.makedirs(GENERATED_FOLDER, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)

MODEL_OPTIONS = [
    "./models/kokoro-v1.0.onnx",
    "./models/model_fp16.onnx",
    "./models/model_q4.onnx",
    "./models/model_q4f16.onnx",
    "./models/model_q8f16.onnx",
    "./models/model_quantized.onnx",
    "./models/model_uint8.onnx",
    "./models/model_uint8f16.onnx",
]

MALE_VOICES = [
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
    "am_michael", "am_onyx", "am_puck", "am_santa",
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis"
]
FEMALE_VOICES = [
    "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica",
    "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah",
    "af_sky", "bf_alice", "bf_emma", "bf_isabella", "bf_lily"
]

# Pick your default Gemini model here (you can change in code later if needed)
GEMINI_MODEL = "models/gemini-1.5-flash"  # fast/cheap; set GOOGLE_API_KEY in .env

# =========================================================
# Utils
# =========================================================
def clear_generated_folder():
    for fn in os.listdir(GENERATED_FOLDER):
        fp = os.path.join(GENERATED_FOLDER, fn)
        if os.path.isfile(fp):
            try:
                os.remove(fp)
            except Exception:
                pass

def safe_stem(name: str) -> str:
    base = os.path.splitext(os.path.basename(name))[0]
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", base)[:60] or str(uuid.uuid4())[:8]

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def numpy_to_audio_segment(audio_np: np.ndarray, sample_rate: int) -> AudioSegment:
    audio_int16 = (np.clip(audio_np, -1.0, 1.0) * 32767).astype(np.int16)
    return AudioSegment(
        data=audio_int16.tobytes(),
        sample_width=audio_int16.dtype.itemsize,
        frame_rate=sample_rate,
        channels=1
    )

def overlay_appreciative_gesture(main_segment: AudioSegment, gesture_segment: AudioSegment) -> AudioSegment:
    if len(main_segment) == 0 or len(gesture_segment) == 0:
        return main_segment
    offset = int(random.uniform(0.2, 0.8) * len(main_segment))
    return main_segment.overlay(gesture_segment, position=offset)

def parse_script(script_text: str) -> List[Tuple[str, str]]:
    pairs = []
    for raw in script_text.splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        speaker, text = line.split(":", 1)
        speaker = speaker.strip().lower()
        text = text.strip()
        if text:
            pairs.append((speaker, text))
    return pairs

def extend_music_to_length(music: AudioSegment, target_ms: int) -> AudioSegment:
    if len(music) == 0:
        return music
    reps = (target_ms // len(music)) + 1
    extended = music * reps
    return extended[:target_ms]


def zip_files(file_paths: List[str], zip_name: str) -> str:
    """Zips a list of files into a single archive."""
    zip_path = os.path.join(GENERATED_FOLDER, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in file_paths:
            if os.path.exists(fp):
                zf.write(fp, arcname=os.path.basename(fp))
    return zip_path

def list_project_ids() -> List[str]:
    out = []
    for pid in os.listdir(PROJECTS_DIR):
        pdir = os.path.join(PROJECTS_DIR, pid)
        if os.path.isdir(pdir) and os.path.exists(os.path.join(pdir, "meta.json")):
            out.append(pid)
    return sorted(out)

def load_script_from_meta(pid: str) -> List[str]:
    meta_path = os.path.join(PROJECTS_DIR, pid, "meta.json")
    if not os.path.exists(meta_path):
        return []
    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            meta = json.load(fh)
    except Exception:
        return []
    script = meta.get("script", [])
    if isinstance(script, str):
        script = [s for s in script.splitlines() if s.strip()]
    return script

def default_output_name_for_pid(pid: str) -> str:
    meta_path = os.path.join(PROJECTS_DIR, pid, "meta.json")
    title_stub = pid
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as fh:
                meta = json.load(fh)
            title = meta.get("title", "") or pid
            title_stub = safe_stem(title)
        except Exception:
            title_stub = pid
    return f"{title_stub}.mp3"

# =========================================================
# TTS Core
# =========================================================
def process_script(
    script_text: str,
    output_file: str,
    model_path: str,
    voice_config_path: str,
    male_voice: str,
    female_voice: str,
    random_pause_enabled: bool,
    pause_min_sec: float,
    pause_max_sec: float,
    enable_gestures: bool,
    gesture_prob: float,
    gesture_phrases_csv: str,
    enable_bg_music: bool,
    bg_choice_name: str,
    bg_map: dict,
    bg_reduction_db: int,
    add_bg_end: bool,
    bg_end_duration_sec: int,
    kokoro=None,
    progress=None,
):
    t0 = time.time()
    if kokoro is None:
        if progress: progress(0.0, desc="Initializing TTS")
        kokoro = Kokoro(model_path, voice_config_path)

    voices = {"male": male_voice, "female": female_voice}
    default_voice = male_voice
    gesture_phrases = [p.strip() for p in gesture_phrases_csv.split(",") if p.strip()]
    pairs = parse_script(script_text)

    if not pairs:
        return None, None, "**No valid 'Speaker: text' lines found in the script.**"

    audio_segments = []
    sample_rate_ref = None
    total = len(pairs)

    for idx, (speaker, text) in enumerate(pairs):
        if progress: progress((idx + 1) / (total + 1), desc=f"TTS line {idx+1}/{total}")
        voice = voices.get(speaker, default_voice)
        samples, sr = kokoro.create(text, voice=voice, speed=1.0, lang="en-us")
        if sample_rate_ref is None:
            sample_rate_ref = sr
        main_seg = numpy_to_audio_segment(samples, sr)

        if enable_gestures and random.random() < float(gesture_prob) and gesture_phrases:
            gesture_voice = voices["female"] if speaker == "male" else voices["male"]
            g_text = random.choice(gesture_phrases)
            g_samples, _ = kokoro.create(g_text, voice=gesture_voice, speed=1.0, lang="en-us")
            g_seg = numpy_to_audio_segment(g_samples, sr)
            main_seg = overlay_appreciative_gesture(main_seg, g_seg)

        audio_segments.append(main_seg)
        pause_sec = random.uniform(pause_min_sec, pause_max_sec) if random_pause_enabled else pause_max_sec
        if pause_sec > 0:
            audio_segments.append(AudioSegment.silent(duration=int(pause_sec * 1000)))

    try:
        final_audio = sum(audio_segments)
    except TypeError:
        return None, None, "**Failed to build final audio.**"

    bg_file_path = None
    if enable_bg_music and bg_choice_name and bg_map and bg_choice_name in bg_map:
        bg_file_path = bg_map[bg_choice_name]
        try:
            bg = AudioSegment.from_file(bg_file_path, format="mp3")
            if sample_rate_ref:
                bg = bg.set_frame_rate(sample_rate_ref).set_channels(1)
            bg = bg - int(bg_reduction_db)
            bg = extend_music_to_length(bg, len(final_audio))
            final_audio = final_audio.overlay(bg)
        except Exception as e:
            print("[BG overlay warning]", e)

    if enable_bg_music and add_bg_end and bg_file_path:
        try:
            tail_bg = AudioSegment.from_file(bg_file_path, format="mp3")
            if sample_rate_ref:
                tail_bg = tail_bg.set_frame_rate(sample_rate_ref).set_channels(1)
            tail_bg = tail_bg - int(bg_reduction_db)
            final_audio += tail_bg[: int(bg_end_duration_sec * 1000)]
        except Exception as e:
            print("[BG tail warning]", e)

    out_path = os.path.join(GENERATED_FOLDER, output_file)
    final_audio.export(out_path, format="mp3")
    dur_sec = len(final_audio) / 1000.0
    elapsed = time.time() - t0
    md = f"**Created:** `{out_path}`  \n**Length:** {dur_sec:.2f}s  \n**Processing:** {elapsed:.2f}s"
    if progress: progress(1.0, desc="Done")
    return out_path, out_path, md

# =========================================================
# Gemini PDF → JSON
# =========================================================
def ensure_gemini():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in environment.")
    genai.configure(api_key=api_key)

def read_pdf_text(path: str, max_chars: int = 200_000) -> str:
    reader = PdfReader(path)
    chunks = []
    total = 0
    for page in reader.pages:
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        if t:
            chunks.append(t)
            total += len(t)
        if total > max_chars:
            break
    return "\n\n".join(chunks)[:max_chars]

def gemini_extract_metadata_and_script(pdf_path: str) -> Dict[str, Any]:
    ensure_gemini()
    model = genai.GenerativeModel(GEMINI_MODEL)

    file_obj = None
    try:
        file_obj = genai.upload_file(pdf_path)
    except Exception as e:
        print("[Gemini upload warning]", e)

    text_snippet = read_pdf_text(pdf_path, max_chars=120_000)

    system = "You are an expert scientific editor. Extract structured metadata and produce a short summary and a two-speaker podcast script."

    prompt_head = """
Given this research paper, extract fields and generate a brief:
Return valid JSON only with keys:
conference, year, link, domain, title, summary, tags, script

- conference: string (guess if missing, else "Unknown")
- year: integer (guess from paper; else current year)
- link: canonical URL (arXiv/DOI if present, else "Unknown")
- domain: broad area like "AI", "NLP", "CV", "Robotics", "Genomics"
- title: paper title
- summary: <= 120 words, non-hallucinated
- tags: comma-separated keywords
- script: array of lines formatted exactly "Male: ..." or "Female: ...". 10-16 lines total, concise.

STRICT FORMAT EXAMPLE:
{
  "conference": "NeurIPS",
  "year": 2024,
  "link": "https://arxiv.org/abs/2410.12345",
  "domain": "AI",
  "title": "Paper Title",
  "summary": "Short abstract-like summary...",
  "tags": "SSM, long-context, music",
  "script": [
    "Male: Welcome...",
    "Female: Today we cover...",
    "Male: Key idea is...",
    "Female: Implications include..."
  ]
}
""".strip()

    prompt_tail = (
        "Paper text (snippet for grounding, may be partial):\n```\n"
        + text_snippet[:6000]
        + "\n```"
    )

    try:
        if file_obj is not None:
            resp = model.generate_content([system, prompt_head, prompt_tail, file_obj])
        else:
            resp = model.generate_content([system, prompt_head, prompt_tail])
        txt = resp.text
    except Exception as e:
        raise RuntimeError(f"Gemini call failed: {e}")

    try:
        m = re.search(r"\{.*\}", txt, re.S)
        data = json.loads(m.group(0) if m else txt)
    except Exception as e:
        raise RuntimeError(f"Failed to parse JSON from Gemini response: {e}\nRaw: {txt[:500]}")

    out: Dict[str, Any] = {}
    out["conference"] = data.get("conference", "Unknown")
    try:
        out["year"] = int(data.get("year", datetime.now().year))
    except Exception:
        out["year"] = datetime.now().year
    out["link"] = data.get("link", "Unknown")
    out["domain"] = data.get("domain", "Unknown")
    out["title"] = data.get("title", "Unknown Title")
    out["summary"] = data.get("summary", "")
    out["tags"] = data.get("tags", "")
    script = data.get("script", [])
    if isinstance(script, str):
        script = [s for s in script.splitlines() if s.strip()]
    out["script"] = script
    return out

def write_project_json(project_id: str, payload: Dict[str, Any]) -> str:
    folder = os.path.join(PROJECTS_DIR, project_id)
    os.makedirs(folder, exist_ok=True)
    meta_path = os.path.join(folder, "meta.json")

    base = {
        "id": project_id,
        "conference": payload.get("conference", "Unknown"),
        "year": int(payload.get("year", datetime.now().year)),
        "link": payload.get("link", "Unknown"),
        "domain": payload.get("domain", "Unknown"),
        "title": payload.get("title", "Unknown Title"),
        "summary": payload.get("summary", ""),
        "tags": payload.get("tags", ""),
        "date_added": now_iso(),
        "ready_to_publish": bool(payload.get("ready_to_publish", False)),
        "script": payload.get("script", []),
    }

    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as fh:
                old = json.load(fh)
        except Exception:
            old = {}
        old.update(base)
        base = old

    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(base, fh, ensure_ascii=False, indent=2)
    return meta_path

# =========================================================
# Extra helpers for the two new pages
# =========================================================
def list_generated_mp3s() -> List[str]:
    files = []
    for fn in sorted(os.listdir(GENERATED_FOLDER)):
        if fn.lower().endswith(".mp3"):
            files.append(os.path.join(GENERATED_FOLDER, fn))
    return files

def mp3_choices() -> List[str]:
    # Return relative names for UI listing
    return [os.path.basename(p) for p in list_generated_mp3s()]

def mp3_path_from_choice(choice: str) -> str:
    return os.path.join(GENERATED_FOLDER, choice)

def zip_all_podcasts() -> str:
    files = list_generated_mp3s()
    if not files:
        return None
    zip_name = f"all_podcasts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path = os.path.join(GENERATED_FOLDER, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in files:
            zf.write(fp, arcname=os.path.basename(fp))
    return zip_path

def read_all_project_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    fields = ["id","conference","year","link","domain","title","summary","tags","date_added","ready_to_publish"]
    for pid in list_project_ids():
        meta_path = os.path.join(PROJECTS_DIR, pid, "meta.json")
        try:
            with open(meta_path, "r", encoding="utf-8") as fh:
                meta = json.load(fh)
        except Exception:
            meta = {}
        row = {k: meta.get(k, "") for k in fields}
        # add derived fields (optional): script length
        script_val = meta.get("script", [])
        if isinstance(script_val, list):
            row["script_lines"] = len(script_val)
        else:
            row["script_lines"] = 0
        rows.append(row)
    return rows

def write_projects_csv(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return None
    fields = list(rows[0].keys())
    csv_name = f"projects_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    csv_path = os.path.join(PROJECTS_DIR, csv_name)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return csv_path

# =========================================================
# Gradio UI
# =========================================================
with gr.Blocks(title="Sid's Research App", theme="soft") as demo:
    gr.Markdown("# Sid’s Research App")
    gr.Markdown(
        "Tabs: **PDF → Gemini Metadata**, **TTS Generation**, **Generated Podcasts**, **Projects Table**. "
        "Per-paper JSON is stored under `projects/{id}/meta.json`."
    )

    bg_map_state = gr.State({})  # TTS BG track name -> path mapping

    with gr.Tabs() as tabs:
        # -----------------------------------
        # Tab 1: PDF → Gemini Metadata
        # -----------------------------------
        with gr.Tab("1) PDF → Gemini: Metadata + Summary + Script"):
            gr.Markdown("### Drop PDFs. Get JSON with metadata, summary, tags, and a Male/Female script. Stored in `projects/{id}/meta.json`.")
            with gr.Row():
                with gr.Column(scale=1):
                    pdf_files = gr.File(label="Upload PDFs", file_count="multiple", file_types=[".pdf"])
                    gemini_btn = gr.Button("Extract with Gemini ✨", variant="primary")
                    ready_toggle = gr.Checkbox(value=False, label="Mark ready_to_publish in JSON")
                with gr.Column(scale=1):
                    json_log = gr.Markdown()
                    zip_json_btn = gr.Button("Download all JSON as ZIP")
                    zip_json_out = gr.File(label="JSON ZIP")

            def do_extract(pdf_files, ready_toggle):
                if not pdf_files:
                    return "**No PDFs provided.**"
                ensure_gemini()
                logs = []
                for f in pdf_files:
                    proj_id = str(uuid.uuid4())
                    folder = os.path.join(PROJECTS_DIR, proj_id)
                    os.makedirs(folder, exist_ok=True)
                    dest_pdf = os.path.join(folder, os.path.basename(f.name))
                    try:
                        shutil.copyfile(f.name, dest_pdf)
                    except Exception:
                        with open(f.name, "rb") as src, open(dest_pdf, "wb") as dst:
                            dst.write(src.read())

                    try:
                        data = gemini_extract_metadata_and_script(dest_pdf)
                        data["ready_to_publish"] = bool(ready_toggle)
                        meta_path = write_project_json(proj_id, data)
                        logs.append(f"- ✅ `{os.path.basename(dest_pdf)}` → `{meta_path}`")
                    except Exception as e:
                        logs.append(f"- ❌ `{os.path.basename(dest_pdf)}` → Error: {e}")

                return "### Results\n" + "\n".join(logs)

            gemini_btn.click(
                fn=do_extract,
                inputs=[pdf_files, ready_toggle],
                outputs=[json_log],
            )

            def zip_all_json():
                zip_name = f"project_json_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                zip_path = os.path.join(PROJECTS_DIR, zip_name)
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for pid in os.listdir(PROJECTS_DIR):
                        pdir = os.path.join(PROJECTS_DIR, pid)
                        if not os.path.isdir(pdir):
                            continue
                        meta = os.path.join(pdir, "meta.json")
                        if os.path.exists(meta):
                            zf.write(meta, arcname=os.path.join(pid, "meta.json"))
                return zip_path

            zip_json_btn.click(fn=zip_all_json, inputs=None, outputs=[zip_json_out])

        # -----------------------------------
        # Tab 2: TTS Generator
        # -----------------------------------
        with gr.Tab("2) TTS Generator"):
            gr.Markdown("### Generate podcasts from scripts or from project JSONs")

            with gr.Row():
                with gr.Column(scale=1):
                    model_path = gr.Dropdown(MODEL_OPTIONS, value=MODEL_OPTIONS[0], label="Model Path")
                    voice_config = gr.Textbox(value="voices-v1.0.bin", label="Voice Config Path")

                    male_voice_dd = gr.Dropdown(MALE_VOICES, value=MALE_VOICES[0], label="Male Voice")
                    female_voice_dd = gr.Dropdown(FEMALE_VOICES, value=FEMALE_VOICES[0], label="Female Voice")

                    random_pause = gr.Checkbox(value=True, label="Enable Random Pause")
                    pause_min = gr.Slider(0.1, 1.0, value=0.2, step=0.1, label="Pause Min Duration (sec)")
                    pause_max = gr.Slider(0.1, 2.0, value=0.4, step=0.1, label="Pause Max Duration (sec)")

                    enable_gestures = gr.Checkbox(value=False, label="Enable Appreciative Gestures")
                    gesture_prob = gr.Slider(0.0, 1.0, value=0.2, step=0.1, label="Gesture Probability")
                    gesture_phrases = gr.Textbox(value="yeah, uh-huh, right, ok", label="Gesture Phrases (comma-separated)")

                    enable_bg = gr.Checkbox(value=True, label="Enable Background Music")
                    bg_files = gr.File(label="Upload Background Tracks (MP3)", file_count="multiple", file_types=[".mp3"])
                    bg_select = gr.Dropdown(choices=[], label="Select Background Track")
                    bg_reduce = gr.Slider(0, 40, value=20, step=1, label="Background Music Volume Reduction (dB)")
                    add_bg_tail = gr.Checkbox(value=True, label="Append Extra Background Music at End")
                    bg_tail_sec = gr.Slider(1, 10, value=3, step=1, label="Extra Background Music Duration (sec)")

                with gr.Column(scale=1):
                    with gr.Tab("Single Script"):
                        final_name = gr.Textbox(value="podcast_episode.mp3", label="Final Podcast File Name")
                        script_area = gr.TextArea(value="Male:\nFemale:\n", label="Script (Speaker: text per line)", lines=14)
                        gen_btn = gr.Button("Generate ✨", variant="primary")
                        audio_preview = gr.Audio(label="Preview", type="filepath")
                        file_download = gr.File(label="Download Podcast")
                        metrics_md = gr.Markdown()

                    with gr.Tab("Batch: TXT files"):
                        batch_txts = gr.File(label="Upload Script TXT Files", file_count="multiple", file_types=[".txt"])
                        gen_batch_btn = gr.Button("Generate Batch ✨", variant="primary")
                        zip_out = gr.File(label="Download All Podcasts (ZIP)")
                        batch_md = gr.Markdown()

                    with gr.Tab("Batch: From JSON projects"):
                        refresh_btn = gr.Button("Refresh project list")
                        project_list = gr.CheckboxGroup(choices=[], label="Select project IDs (meta.json required)")
                        gen_from_json_btn = gr.Button("Generate from JSON ✨", variant="primary")
                        zip_out_json = gr.File(label="Download All Podcasts (ZIP)")
                        batch_json_md = gr.Markdown()

            bg_map_state = gr.State({})

            def on_bg_files_uploaded(files):
                mapping = {}
                names = []
                if files:
                    for f in files:
                        names.append(os.path.basename(f.name))
                        mapping[os.path.basename(f.name)] = f.name
                value = names[0] if names else None
                return gr.update(choices=names, value=value), mapping

            bg_files.upload(
                fn=on_bg_files_uploaded,
                inputs=[bg_files],
                outputs=[bg_select, bg_map_state],
            )

            def do_single(
                final_name,
                script_area,
                model_path, voice_config, male_voice_dd, female_voice_dd,
                random_pause, pause_min, pause_max,
                enable_gestures, gesture_prob, gesture_phrases,
                enable_bg, bg_select, bg_map_state, bg_reduce, add_bg_tail, bg_tail_sec
            ):
                clear_generated_folder()
                if not final_name.lower().endswith(".mp3"):
                    final_name = final_name + ".mp3"

                def _progress(frac, desc=""):
                    return

                audio_path, file_path, md = process_script(
                    script_text=script_area,
                    output_file=final_name,
                    model_path=model_path,
                    voice_config_path=voice_config,
                    male_voice=male_voice_dd,
                    female_voice=female_voice_dd,
                    random_pause_enabled=bool(random_pause),
                    pause_min_sec=float(pause_min),
                    pause_max_sec=float(pause_max),
                    enable_gestures=bool(enable_gestures),
                    gesture_prob=float(gesture_prob),
                    gesture_phrases_csv=gesture_phrases,
                    enable_bg_music=bool(enable_bg),
                    bg_choice_name=bg_select,
                    bg_map=bg_map_state or {},
                    bg_reduction_db=int(bg_reduce),
                    add_bg_end=bool(add_bg_tail),
                    bg_end_duration_sec=int(bg_tail_sec),
                    kokoro=None,
                    progress=_progress,
                )
                return audio_path, file_path, md

            gen_btn.click(
                fn=do_single,
                inputs=[
                    final_name, script_area,
                    model_path, voice_config, male_voice_dd, female_voice_dd,
                    random_pause, pause_min, pause_max,
                    enable_gestures, gesture_prob, gesture_phrases,
                    enable_bg, bg_select, bg_map_state, bg_reduce, add_bg_tail, bg_tail_sec
                ],
                outputs=[audio_preview, file_download, metrics_md],
            )

            def do_batch_txt(
                batch_txts,
                model_path, voice_config, male_voice_dd, female_voice_dd,
                random_pause, pause_min, pause_max,
                enable_gestures, gesture_prob, gesture_phrases,
                enable_bg, bg_select, bg_map_state, bg_reduce, add_bg_tail, bg_tail_sec
            ):
                clear_generated_folder()
                if not batch_txts:
                    return None, "**No TXT files provided.**"
                try:
                    kokoro = Kokoro(model_path, voice_config)
                except Exception as e:
                    return None, f"**Failed to initialize TTS model:** {e}"

                results = []
                for f in batch_txts:
                    try:
                        with open(f.name, "r", encoding="utf-8") as fh:
                            content = fh.read()
                    except Exception:
                        with open(f.name, "rb") as fh:
                            content = fh.read().decode("utf-8", errors="ignore")

                    base = safe_stem(f.name)
                    out_file = f"{base}.mp3"

                    audio_path, _, md = process_script(
                        script_text=content,
                        output_file=out_file,
                        model_path=model_path,
                        voice_config_path=voice_config,
                        male_voice=male_voice_dd,
                        female_voice=female_voice_dd,
                        random_pause_enabled=bool(random_pause),
                        pause_min_sec=float(pause_min),
                        pause_max_sec=float(pause_max),
                        enable_gestures=bool(enable_gestures),
                        gesture_prob=float(gesture_prob),
                        gesture_phrases_csv=gesture_phrases,
                        enable_bg_music=bool(enable_bg),
                        bg_choice_name=bg_select,
                        bg_map=bg_map_state or {},
                        bg_reduction_db=int(bg_reduce),
                        add_bg_end=bool(add_bg_tail),
                        bg_end_duration_sec=int(bg_tail_sec),
                        kokoro=kokoro,
                        progress=None,
                    )
                    results.append(f"- **{out_file}** → {md if md else 'ok'}")

                zip_name = f"podcasts_txt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                zip_path = os.path.join(GENERATED_FOLDER, zip_name)
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for mp3_file in os.listdir(GENERATED_FOLDER):
                        if mp3_file.lower().endswith(".mp3"):
                            zf.write(os.path.join(GENERATED_FOLDER, mp3_file), mp3_file)
                md = "### Batch Results (TXT)\n" + "\n".join(results)
                return zip_path, md

            gen_batch_btn.click(
                fn=do_batch_txt,
                inputs=[
                    batch_txts,
                    model_path, voice_config, male_voice_dd, female_voice_dd,
                    random_pause, pause_min, pause_max,
                    enable_gestures, gesture_prob, gesture_phrases,
                    enable_bg, bg_select, bg_map_state, bg_reduce, add_bg_tail, bg_tail_sec
                ],
                outputs=[zip_out, batch_md],
            )

            def refresh_projects():
                return gr.update(choices=list_project_ids(), value=[])

            refresh_btn.click(fn=refresh_projects, inputs=None, outputs=[project_list])

            def do_batch_from_json(
                selected_pids: List[str],
                model_path, voice_config, male_voice_dd, female_voice_dd,
                random_pause, pause_min, pause_max,
                enable_gestures, gesture_prob, gesture_phrases,
                enable_bg, bg_select, bg_map_state, bg_reduce, add_bg_tail, bg_tail_sec
            ):
                clear_generated_folder()
                if not selected_pids:
                    return None, "**No projects selected.**"
                try:
                    kokoro = Kokoro(model_path, voice_config)
                except Exception as e:
                    return None, f"**Failed to initialize TTS model:** {e}"

                results = []
                for pid in selected_pids:
                    script_lines = load_script_from_meta(pid)
                    if not script_lines:
                        results.append(f"- ❌ `{pid}` → No script found in meta.json")
                        continue
                    script_text = "\n".join(script_lines)
                    out_file = default_output_name_for_pid(pid)

                    audio_path, _, md = process_script(
                        script_text=script_text,
                        output_file=out_file,
                        model_path=model_path,
                        voice_config_path=voice_config,
                        male_voice=male_voice_dd,
                        female_voice=female_voice_dd,
                        random_pause_enabled=bool(random_pause),
                        pause_min_sec=float(pause_min),
                        pause_max_sec=float(pause_max),
                        enable_gestures=bool(enable_gestures),
                        gesture_prob=float(gesture_prob),
                        gesture_phrases_csv=gesture_phrases,
                        enable_bg_music=bool(enable_bg),
                        bg_choice_name=bg_select,
                        bg_map=bg_map_state or {},
                        bg_reduction_db=int(bg_reduce),
                        add_bg_end=bool(add_bg_tail),
                        bg_end_duration_sec=int(bg_tail_sec),
                        kokoro=kokoro,
                        progress=None,
                    )
                    results.append(f"- **{out_file}** ← `{pid}` → {md if md else 'ok'}")

                zip_name = f"podcasts_json_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                zip_path = os.path.join(GENERATED_FOLDER, zip_name)
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for mp3_file in os.listdir(GENERATED_FOLDER):
                        if mp3_file.lower().endswith(".mp3"):
                            zf.write(os.path.join(GENERATED_FOLDER, mp3_file), mp3_file)
                md = "### Batch Results (JSON projects)\n" + "\n".join(results)
                return zip_path, md

            gen_from_json_btn.click(
                fn=do_batch_from_json,
                inputs=[
                    project_list,
                    model_path, voice_config, male_voice_dd, female_voice_dd,
                    random_pause, pause_min, pause_max,
                    enable_gestures, gesture_prob, gesture_phrases,
                    enable_bg, bg_select, bg_map_state, bg_reduce, add_bg_tail, bg_tail_sec
                ],
                outputs=[zip_out_json, batch_json_md],
            )

        # -----------------------------------
        # Tab 3: Generated Podcasts (new)
        # -----------------------------------
        with gr.Tab("3) Generated Podcasts"):
            gr.Markdown("### Browse and play all MP3s in `generated_podcasts/`")

            refresh_pod_btn = gr.Button("Refresh list")
            podcast_radio = gr.Radio(choices=[], label="Select a podcast")
            audio_player = gr.Audio(label="Preview", type="filepath")
            files_list = gr.Files(label="All podcast files")
            zip_all_btn = gr.Button("Download ZIP of all podcasts")
            zip_all_out = gr.File(label="Podcasts ZIP")

            def refresh_podcasts():
                choices = mp3_choices()
                files = list_generated_mp3s()
                selected = choices[0] if choices else None
                audio_path = mp3_path_from_choice(selected) if selected else None
                return gr.update(choices=choices, value=selected), audio_path, files

            refresh_pod_btn.click(
                fn=refresh_podcasts,
                inputs=None,
                outputs=[podcast_radio, audio_player, files_list],
            )

            def on_select(choice):
                if not choice:
                    return None
                return mp3_path_from_choice(choice)

            podcast_radio.change(
                fn=on_select,
                inputs=[podcast_radio],
                outputs=[audio_player],
            )

            zip_all_btn.click(
                fn=zip_all_podcasts,
                inputs=None,
                outputs=[zip_all_out],
            )

        # -----------------------------------
        # Tab 4: Projects Table (new)
        # -----------------------------------
        with gr.Tab("4) Projects Table"):
            gr.Markdown("### Table view of all `meta.json` files in `projects/`")
            refresh_tbl_btn = gr.Button("Refresh table")
            df = gr.Dataframe(headers=["id","conference","year","link","domain","title","summary","tags","date_added","ready_to_publish","script_lines"],
                              value=[],
                              wrap=True,
                              interactive=False,
                              row_count=(0, "dynamic"),
                              col_count=(11, "fixed"),
                              label="Projects")

            csv_btn = gr.Button("Download CSV")
            csv_out = gr.File(label="Projects CSV")

            def refresh_table():
                rows = read_all_project_rows()
                # Convert to matrix for Gradio Dataframe
                headers = ["id","conference","year","link","domain","title","summary","tags","date_added","ready_to_publish","script_lines"]
                matrix = [[r.get(h, "") for h in headers] for r in rows]
                return gr.update(value=matrix)

            refresh_tbl_btn.click(fn=refresh_table, inputs=None, outputs=[df])

            def export_csv():
                rows = read_all_project_rows()
                return write_projects_csv(rows)

            csv_btn.click(fn=export_csv, inputs=None, outputs=[csv_out])

# demo.queue(concurrency_count=1)  # enable if needed
if __name__ == "__main__":
    demo.launch()
