Project description:
Music platform for matching songs to user-submitted videos. Simple Web UI where you select a video, then the server returns top 5 song matches.

The ML logic skips using actual video and music embeddings. Instead, key frames (3-5 images) are extracted directly in the browser from the selected video. The frontend uploads only these images, and the backend reads a prepared list of tags->song. Then it uses an ML model (like CLIP or Gemini) to find matching tags for the images. 

Project tech stack:
* Web frontend - Nuxt with Vue.js, minimal demo page. Extracts frames from the video client-side (using HTML5 `<video>` and `<canvas>`) and uploads only the images, waiting for a server response.
* Storage - Local MinIO instance (S3-like) for storing uploaded images and served songs.
* Songs database - A simple CSV file with the name of the song, tags, and path to the file on storage.
* Tag Embeddings database - Embedded ChromaDB running locally inside the Python process to store and query tag embeddings.
* ML module - Dockerized FastAPI serving endpoints:
    * Task start endpoint - accepts the uploaded images, saves them to MinIO, and starts a background task. 
    * Task status - returns either UNKNOWN_ID, RUNNING, or COMPLETED. State is managed purely in-memory (using a Python dictionary) since this is a PoC with a single ML service instance.
    * Task results - if status is COMPLETED, returns the top 5 picks that match the songs database. Otherwise returns an error.

Project structure:
* The ML logic uses an abstraction layer for its "backends" (e.g., a `TagMatcher` interface). 
    * The Gemini backend calls the Gemini API (via `google-genai` and pydantic), passing the images and text tags to find the best match. 
    * The CLIP backend calculates image embeddings locally. It retrieves pre-calculated tag embeddings from ChromaDB (or calculates and caches them if missing), and performs similarity matching.
* There is no message queue (like Kafka) or load balancer. The architecture is kept simple for the PoC, relying on a single FastAPI instance and in-memory task tracking.

Key optimisations:
* Client-Side Frame Extraction: By extracting frames locally in the browser, we avoid uploading massive video files and offload processing from the server, saving significant bandwidth and storage.
* Precalculated Tag Embeddings: For the CLIP backend, tag embeddings are stored in ChromaDB. When matching to images, we only need to calculate the image embeddings (3-5 images) and then perform a fast similarity search against the precalculated tag vectors in ChromaDB.

## Setup & Installation Guide

### Prerequisites
- **Python 3.12+** and the **`uv`** package manager (for the FastAPI backend).
- **Node.js 22+** (for the Nuxt 3 frontend).
- A **Gemini API Key** (optional, required only if you want to use the Gemini AI engine instead of local CLIP).

### 1. Configuration & Music Library
1. Clone the repository.
2. In the root directory, create a `.env` file and add your Gemini API key (if applicable):
   ```env
   GEMINI_API_KEY=your_google_gemini_key_here
   ```
3. Add your local `.mp3` or `.wav` music files into the `music_library/` folder.
4. Update `music_library/metadata.csv` to map each song's title, author, comma-separated tags, and precise filename.

### 2. Starting the Backend
The backend serves the ML API and static music files on port `8000`. Start it easily using the provided script:
```bash
bash scripts/start_backend.sh
```
*(Alternatively, navigate to `ml_core/` and run `uv run uvicorn main:app --host 0.0.0.0 --port 8000`).*

### 3. Starting the Frontend
The frontend interface runs on port `3000`. First, navigate to the `frontend/` directory and install the required NPM dependencies:
```bash
cd frontend
npm install
```
Then start the development server using the provided script (which automatically attempts to switch to Node 22 via `nvm`):
```bash
cd ..
bash scripts/start_frontend.sh
```
*(Alternatively, navigate to `frontend/` and run `npm run dev`).*

### 4. Running the Tests
To run the automated test suite for the ML matching models, you can easily execute it directly from the VS Code Testing GUI. 

Alternatively, to run the tests from the terminal, execute:
```bash
uv run pytest ml_core/tests/
```