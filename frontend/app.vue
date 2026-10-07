<template>
  <div class="app-wrapper">
    <header class="app-header">
      <div class="header-content">
        <h1>Sync&nbsp;<span>Sound</span></h1>
        <p>AI-powered music recommendation for your videos</p>
      </div>
    </header>
    
    <main class="container">
      <div class="card upload-section">
        <h2>Upload Video</h2>
        <p class="upload-hint">Select a local video file to get started</p>
        
        <label class="file-label">
          <input type="file" accept="video/*" @change="onVideoSelected" class="file-input" />
          <span>Choose File</span>
        </label>
        
        <div v-if="videoFile" class="file-info fade-in">
          <span class="file-name">{{ videoFile.name }}</span> 
          <span class="file-size">({{ (videoFile.size / 1024 / 1024).toFixed(2) }} MB)</span>
          
          <div v-if="videoObjectUrl" class="video-preview-wrapper mt-3">
            <video :src="videoObjectUrl" controls class="preview-video"></video>
          </div>
        </div>
      </div>

      <div class="card controls-section">
        <div class="actions">
          <div class="model-select-wrapper">
            <label for="modelSelect">AI Engine:</label>
            <select id="modelSelect" v-model="selectedModel" :disabled="isProcessing" class="styled-select">
              <option value="clip">Local CLIP (Fast)</option>
              <option value="gemini">Gemini API</option>
            </select>
          </div>
          
          <button class="primary-btn" :disabled="!videoFile || isProcessing" @click="startProcess">
            <span v-if="isProcessing" class="spinner"></span>
            {{ isProcessing ? 'Analyzing...' : 'Find Matches' }}
          </button>
        </div>

        <div v-if="statusMessage" class="status-bar slide-down">
          <div class="status-indicator" :class="{ processing: isProcessing, done: statusMessage === 'Done!' }"></div>
          {{ statusMessage }}
        </div>
      </div>

      <!-- Hidden canvas for frame extraction -->
      <canvas ref="canvasRef" style="display: none;"></canvas>

      <div v-if="recommendedSongs.length > 0" class="card results-section fade-in">
        <h2>Recommended Songs</h2>
        <ul class="results-list">
          <li v-for="(song, idx) in recommendedSongs" :key="idx" class="result-item song-item">
            <div class="song-info">
              <span class="result-rank">#{{ idx + 1 }}</span>
              <div class="song-details">
                <span class="song-title">{{ song.title }}</span>
                <span class="song-author">by {{ song.author }}</span>
                <span class="song-score">Match Score: {{ song.score }}</span>
              </div>
            </div>
            <audio controls class="song-player">
              <source :src="`${API_URL}/music/${song.filename}`" type="audio/mpeg">
            </audio>
          </li>
        </ul>
      </div>

      <!-- Debug Panel -->
      <div class="card debug-section" v-if="extractedFrames.length > 0">
        <button class="debug-toggle" @click="showDebug = !showDebug">
          {{ showDebug ? 'Hide' : 'Show' }} Developer Debug Info
        </button>
        
        <div v-show="showDebug" class="debug-content slide-down">
          <div v-if="recommendedTags.length > 0" class="debug-tags-section">
            <h3>ML Extracted Tags</h3>
            <div class="tags-container">
              <span v-for="tag in recommendedTags" :key="tag" class="debug-tag">{{ tag }}</span>
            </div>
          </div>

          <h3>Extracted Frames (Sent to Backend)</h3>
          <div class="frames-grid">
            <div v-for="(frame, idx) in extractedFrames" :key="idx" class="frame-wrapper">
              <img :src="frame" class="frame-img" />
              <span class="frame-label">Frame {{ idx + 1 }}</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const videoFile = ref(null)
const videoObjectUrl = ref('')
const isProcessing = ref(false)
const statusMessage = ref('')
const extractedFrames = ref([])
const recommendedTags = ref([])
const recommendedSongs = ref([])
const selectedModel = ref('clip')
const canvasRef = ref(null)
const showDebug = ref(false)

const API_URL = 'http://localhost:8000'

const onVideoSelected = (event) => {
  const file = event.target.files[0]
  if (file) {
    videoFile.value = file
    if (videoObjectUrl.value) {
      URL.revokeObjectURL(videoObjectUrl.value)
    }
    videoObjectUrl.value = URL.createObjectURL(file)
    extractedFrames.value = []
    recommendedTags.value = []
    recommendedSongs.value = []
    statusMessage.value = ''
    showDebug.value = false
  }
}

const extractFrames = async (file, numFrames = 5) => {
  return new Promise((resolve, reject) => {
    const videoUrl = URL.createObjectURL(file)
    const video = document.createElement('video')
    video.src = videoUrl
    video.muted = true
    video.playsInline = true
    video.crossOrigin = "anonymous"

    const frames = []
    
    video.onloadeddata = async () => {
      const duration = video.duration
      if (isNaN(duration) || duration === 0) {
        reject(new Error("Invalid video duration"))
        return
      }

      // Calculate time stamps avoiding the absolute very start and end
      const interval = duration / (numFrames + 1)
      const timeStamps = Array.from({ length: numFrames }, (_, i) => interval * (i + 1))

      for (const time of timeStamps) {
        await new Promise((resolveSeek) => {
          video.currentTime = time
          video.onseeked = () => {
            const canvas = canvasRef.value
            canvas.width = video.videoWidth
            canvas.height = video.videoHeight
            const ctx = canvas.getContext('2d')
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
            
            canvas.toBlob((blob) => {
              frames.push({
                blob,
                dataUrl: canvas.toDataURL('image/jpeg', 0.8)
              })
              resolveSeek()
            }, 'image/jpeg', 0.8)
          }
        })
      }
      
      URL.revokeObjectURL(videoUrl)
      resolve(frames)
    }

    video.onerror = (e) => {
      reject(new Error("Error loading video"))
    }
  })
}

const pollStatus = async (taskId) => {
  while (true) {
    const res = await fetch(`${API_URL}/tasks/${taskId}/status`)
    if (!res.ok) throw new Error("Status check failed")
    const data = await res.json()
    
    statusMessage.value = `Backend processing... (${data.status})`
    
    if (data.status === 'COMPLETED') {
      const resultRes = await fetch(`${API_URL}/tasks/${taskId}/results`)
      const resultData = await resultRes.json()
      
      if (resultData.results && resultData.results.songs) {
        recommendedTags.value = resultData.results.tags
        recommendedSongs.value = resultData.results.songs
      } else {
        // Fallback for older responses
        recommendedTags.value = resultData.results || []
      }
      
      isProcessing.value = false
      statusMessage.value = 'Done!'
      break
    } else if (data.status === 'ERROR') {
      isProcessing.value = false
      statusMessage.value = `Error: ${data.error || 'Unknown error during ML processing'}`
      break
    }
    
    // Wait 2 seconds before polling again
    await new Promise(r => setTimeout(r, 2000))
  }
}

const startProcess = async () => {
  if (!videoFile.value) return
  
  isProcessing.value = true
  statusMessage.value = 'Extracting frames in browser...'
  extractedFrames.value = []
  recommendedTags.value = []
  recommendedSongs.value = []
  
  try {
    const frames = await extractFrames(videoFile.value, 5)
    extractedFrames.value = frames.map(f => f.dataUrl)
    
    statusMessage.value = 'Uploading frames to backend...'
    const formData = new FormData()
    formData.append('model', selectedModel.value)
    
    frames.forEach((f, idx) => {
      formData.append('images', f.blob, `frame_${idx}.jpg`)
    })
    
    const response = await fetch(`${API_URL}/tasks`, {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`)
    }
    
    const data = await response.json()
    const taskId = data.task_id
    
    statusMessage.value = 'Backend processing... (RUNNING)'
    await pollStatus(taskId)
    
  } catch (error) {
    console.error(error)
    statusMessage.value = `Error: ${error.message}`
    isProcessing.value = false
  }
}
</script>

<style>
/* Global resets for the app */
body {
  margin: 0;
  background-color: #f4f7f6;
  color: #333;
}
</style>

<style scoped>
.app-wrapper {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  min-height: 100vh;
}

.app-header {
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  color: white;
  padding: 3rem 1rem;
  text-align: center;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  margin-bottom: -3rem;
}

.header-content h1 {
  margin: 0;
  font-size: 2.5rem;
  font-weight: 800;
  letter-spacing: -0.05em;
}

.header-content h1 span {
  color: #fbbf24;
}

.header-content p {
  margin-top: 0.5rem;
  opacity: 0.9;
  font-size: 1.1rem;
}

.container {
  max-width: 700px;
  margin: 0 auto;
  padding: 0 1rem 4rem;
  position: relative;
  z-index: 10;
}

.card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  padding: 2rem;
  margin-bottom: 1.5rem;
}

.upload-section {
  text-align: center;
  border: 2px dashed #e5e7eb;
  transition: border-color 0.3s ease;
}

.upload-section:hover {
  border-color: #a855f7;
}

.upload-icon {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

.upload-section h2 {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
}

.upload-hint {
  color: #6b7280;
  margin-bottom: 1.5rem;
  font-size: 0.95rem;
}

.file-input {
  display: none;
}

.file-label {
  display: inline-block;
  background-color: #f3f4f6;
  color: #4b5563;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.file-label:hover {
  background-color: #e5e7eb;
}

.file-info {
  margin-top: 1rem;
  font-size: 0.9rem;
  color: #10b981;
  font-weight: 500;
}

.file-size {
  color: #6b7280;
  font-weight: normal;
}

.video-preview-wrapper {
  margin-top: 1rem;
}

.preview-video {
  max-width: 100%;
  max-height: 300px;
  border-radius: 8px;
  background-color: #000;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
}

.controls-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

@media (min-width: 500px) {
  .actions {
    flex-direction: row;
    align-items: flex-end;
    justify-content: space-between;
  }
}

.model-select-wrapper {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.model-select-wrapper label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #4b5563;
  margin-bottom: 0.4rem;
}

.styled-select {
  padding: 0.75rem 1rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background-color: #f9fafb;
  font-size: 1rem;
  color: #1f2937;
  outline: none;
  transition: border-color 0.2s;
}

.styled-select:focus {
  border-color: #6366f1;
}

.primary-btn {
  background: #6366f1;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.75rem 2rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-width: 160px;
}

.primary-btn:hover:not(:disabled) {
  background: #4f46e5;
  transform: translateY(-1px);
}

.primary-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.status-bar {
  background-color: #f0fdf4;
  color: #166534;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border: 1px solid #bbf7d0;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #10b981;
}

.status-indicator.processing {
  background-color: #f59e0b;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(245, 158, 11, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
}

.results-section h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  font-size: 1.4rem;
  color: #111827;
}

.results-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.result-item {
  display: flex;
  flex-direction: column;
  padding: 1rem;
  background-color: #f9fafb;
  border-radius: 8px;
  border-left: 4px solid #8b5cf6;
}

.song-info {
  display: flex;
  align-items: center;
  margin-bottom: 0.75rem;
}

.result-rank {
  font-weight: 700;
  color: #8b5cf6;
  margin-right: 1rem;
  font-size: 1.2rem;
  width: 2rem;
}

.song-details {
  display: flex;
  flex-direction: column;
}

.song-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #111827;
}

.song-author {
  font-size: 0.9rem;
  color: #6b7280;
}

.song-score {
  font-size: 0.8rem;
  color: #10b981;
  font-weight: 600;
  margin-top: 0.25rem;
}

.song-player {
  width: 100%;
  height: 40px;
}

.debug-section {
  background-color: #fdfbf7;
  border: 1px solid #e5e7eb;
  padding: 1rem;
}

.debug-toggle {
  background: none;
  border: none;
  color: #6b7280;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0.5rem 0;
  width: 100%;
  text-align: left;
}

.debug-toggle:hover {
  color: #374151;
}

.debug-content {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.debug-content h3 {
  font-size: 1rem;
  margin-top: 0;
  margin-bottom: 0.75rem;
  color: #4b5563;
}

.debug-tags-section {
  margin-bottom: 1.5rem;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.debug-tag {
  background-color: #ede9fe;
  color: #6d28d9;
  padding: 0.25rem 0.75rem;
  border-radius: 16px;
  font-size: 0.85rem;
  font-weight: 500;
}

.frames-grid {
  display: flex;
  gap: 1rem;
  overflow-x: auto;
  padding-bottom: 1rem;
}

.frame-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: center;
  min-width: 120px;
}

.frame-img {
  height: 80px;
  border-radius: 6px;
  object-fit: cover;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.frame-label {
  font-size: 0.75rem;
  color: #6b7280;
}

/* Animations */
.fade-in {
  animation: fadeIn 0.4s ease-in-out;
}

.slide-down {
  animation: slideDown 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
