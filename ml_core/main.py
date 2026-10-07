import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List

from dotenv import load_dotenv
# Load .env from the project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from clip_matcher import ClipMatcher
from gemini_matcher import GeminiMatcher

# In-memory storage for tasks
TASKS: Dict[str, Dict] = {}
# In-memory storage for cached results based on image hashes
CACHE: Dict[str, Dict] = {}

import csv

def load_available_tags():
    tags = set()
    # Resolve path relative to this file
    csv_path = os.path.join(os.path.dirname(__file__), "..", "music_library", "metadata.csv")
    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_tags = [t.strip() for t in row.get("tags", "").split(",") if t.strip()]
                tags.update(row_tags)
    else:
        print("Warning: metadata.csv not found, using fallback tags.")
        tags = {"snow", "christmas", "summer", "sunny", "animal", "pop", "jazz", "classical", "electronic", "concert", "calm", "energetic", "bright", "dark"}
    return list(tags)

AVAILABLE_TAGS = load_available_tags()

# Initialize matchers at startup
matchers = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Initializing matchers...")
    matchers["clip"] = ClipMatcher()
    
    # Only initialize Gemini if key is present
    if os.environ.get("GEMINI_API_KEY"):
        matchers["gemini"] = GeminiMatcher()
    else:
        print("GEMINI_API_KEY not found, GeminiMatcher disabled.")
        
    yield
    # Shutdown (cleanup if needed)

from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the music library to serve MP3 files
music_dir = os.path.join(os.path.dirname(__file__), "..", "music_library")
app.mount("/music", StaticFiles(directory=music_dir), name="music")

async def process_video_frames(task_id: str, image_paths: List[str], model_type: str, cache_key: str = None):
    try:
        if model_type not in matchers:
            raise ValueError(f"Model '{model_type}' is not initialized or invalid.")

        matcher = matchers[model_type]
        
        # Run the heavy ML task in a thread to not block the asyncio event loop
        tags_dict = await asyncio.to_thread(matcher.match, image_paths, AVAILABLE_TAGS, top_k=5)
        
        # Calculate scores for songs
        song_scores = []
        csv_path = os.path.join(music_dir, "metadata.csv")
        if os.path.exists(csv_path):
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    song_tags = [t.strip().lower() for t in row.get("tags", "").split(",") if t.strip()]
                    # count overlap with tags_dict
                    pos_score = sum(1 for tag in tags_dict.get("positive", []) if tag.lower() in song_tags)
                    neg_score = sum(1 for tag in tags_dict.get("negative", []) if tag.lower() in song_tags)
                    score = pos_score - neg_score
                    # We can include songs even with 0 score if we want, but better to rank them
                    song_scores.append({
                        "id": row.get("id"),
                        "title": row.get("title"),
                        "author": row.get("author"),
                        "filename": row.get("filename"),
                        "score": score
                    })
        
        # Sort by score descending
        song_scores.sort(key=lambda x: x["score"], reverse=True)
        top_songs = song_scores[:3]

        TASKS[task_id]["status"] = "COMPLETED"
        TASKS[task_id]["results"] = {
            "tags": tags_dict,
            "songs": top_songs
        }
        if cache_key:
            CACHE[cache_key] = TASKS[task_id]["results"]
    except Exception as e:
        print(f"Error processing task {task_id}:")
        traceback.print_exc()
        TASKS[task_id]["status"] = "ERROR"
        TASKS[task_id]["error"] = str(e)
    finally:
        # We can clean up the temporary image files here if we aren't uploading to MinIO
        for path in image_paths:
            if os.path.exists(path):
                os.remove(path)

@app.post("/tasks")
async def create_task(
    background_tasks: BackgroundTasks,
    images: List[UploadFile] = File(...),
    model: str = Form("clip")
):
    import hashlib
    hasher = hashlib.sha256()
    hasher.update(model.encode('utf-8'))
    
    # Read all images into memory to compute hash
    image_contents = []
    for img in images:
        content = await img.read()
        hasher.update(content)
        image_contents.append(content)
        
    cache_key = hasher.hexdigest()
    task_id = str(uuid.uuid4())
    
    if cache_key in CACHE:
        # Cache hit! Create a completed task immediately
        TASKS[task_id] = {
            "status": "COMPLETED",
            "results": CACHE[cache_key],
            "error": None
        }
        return {"task_id": task_id}
        
    TASKS[task_id] = {"status": "RUNNING", "results": [], "error": None, "cache_key": cache_key}
    
    # Save uploaded images to a temporary local storage
    # In a real app with MinIO, we would upload them there and pass URLs/paths
    os.makedirs("/tmp/ml_core_images", exist_ok=True)
    image_paths = []
    
    for idx, content in enumerate(image_contents):
        # We assume they are image files
        file_path = f"/tmp/ml_core_images/{task_id}_{idx}.jpg"
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        image_paths.append(file_path)

    background_tasks.add_task(process_video_frames, task_id, image_paths, model, cache_key)
    
    return {"task_id": task_id}

import traceback

@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    if task_id not in TASKS:
        return {"status": "UNKNOWN_ID"}
    task = TASKS[task_id]
    if task["status"] == "ERROR":
        return {"status": "ERROR", "error": task.get("error", "Unknown error")}
    return {"status": task["status"]}

@app.get("/tasks/{task_id}/results")
async def get_task_results(task_id: str):
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task = TASKS[task_id]
    if task["status"] != "COMPLETED":
        return JSONResponse(
            status_code=400,
            content={"error": f"Task is currently {task['status']}"}
        )
        
    return {"status": "COMPLETED", "results": task["results"]}


