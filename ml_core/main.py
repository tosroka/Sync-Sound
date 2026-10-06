import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from clip_matcher import ClipMatcher
from gemini_matcher import GeminiMatcher

# In-memory storage for tasks
TASKS: Dict[str, Dict] = {}

# Mock songs database tags (in reality, read from CSV)
AVAILABLE_TAGS = [
    "acoustic", "electronic", "rock", "pop", "jazz", "classical",
    "upbeat", "melancholic", "energetic", "calm", "vocal", "instrumental",
    "a solid red color", "a solid blue color" # for our dummy tests
]

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

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def process_video_frames(task_id: str, image_paths: List[str], model_type: str):
    try:
        if model_type not in matchers:
            raise ValueError(f"Model '{model_type}' is not initialized or invalid.")

        matcher = matchers[model_type]
        
        # Run the heavy ML task in a thread to not block the asyncio event loop
        top_tags = await asyncio.to_thread(matcher.match, image_paths, AVAILABLE_TAGS, top_k=5)
        
        TASKS[task_id]["status"] = "COMPLETED"
        TASKS[task_id]["results"] = top_tags
    except Exception as e:
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
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "RUNNING", "results": [], "error": None}
    
    # Save uploaded images to a temporary local storage
    # In a real app with MinIO, we would upload them there and pass URLs/paths
    os.makedirs("/tmp/ml_core_images", exist_ok=True)
    image_paths = []
    
    for idx, img in enumerate(images):
        # We assume they are image files
        file_path = f"/tmp/ml_core_images/{task_id}_{idx}.jpg"
        with open(file_path, "wb") as buffer:
            buffer.write(await img.read())
        image_paths.append(file_path)

    background_tasks.add_task(process_video_frames, task_id, image_paths, model)
    
    return {"task_id": task_id}

@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    if task_id not in TASKS:
        return {"status": "UNKNOWN_ID"}
    return {"status": TASKS[task_id]["status"]}

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


