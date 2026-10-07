## Video music matcher

Find a background music for your video!

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