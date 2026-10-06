<template>
  <div class="container">
    <h1>Music Recommendation from Video</h1>
    
    <div class="upload-section">
      <input type="file" accept="video/*" @change="onVideoSelected" />
      <div v-if="videoFile" class="file-info">
        Selected: {{ videoFile.name }} ({{ (videoFile.size / 1024 / 1024).toFixed(2) }} MB)
      </div>
    </div>

    <div class="actions">
      <button :disabled="!videoFile || isProcessing" @click="startProcess">
        {{ isProcessing ? 'Processing...' : 'Find Matches' }}
      </button>
      <select v-model="selectedModel" :disabled="isProcessing">
        <option value="clip">Local CLIP</option>
        <option value="gemini">Gemini API</option>
      </select>
    </div>

    <div v-if="statusMessage" class="status">
      Status: {{ statusMessage }}
    </div>

    <!-- Hidden canvas for frame extraction -->
    <canvas ref="canvasRef" style="display: none;"></canvas>

    <div v-if="extractedFrames.length > 0" class="frames-preview">
      <h3>Extracted Frames</h3>
      <div class="frames-grid">
        <img v-for="(frame, idx) in extractedFrames" :key="idx" :src="frame" class="frame-img" />
      </div>
    </div>

    <div v-if="results.length > 0" class="results-section">
      <h2>Recommended Tags / Songs</h2>
      <ul>
        <li v-for="(tag, idx) in results" :key="idx">
          {{ idx + 1 }}. {{ tag }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const videoFile = ref(null)
const isProcessing = ref(false)
const statusMessage = ref('')
const extractedFrames = ref([])
const results = ref([])
const selectedModel = ref('clip')
const canvasRef = ref(null)

const API_URL = 'http://localhost:8000'

const onVideoSelected = (event) => {
  const file = event.target.files[0]
  if (file) {
    videoFile.value = file
    extractedFrames.value = []
    results.value = []
    statusMessage.value = ''
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
      results.value = resultData.results
      isProcessing.value = false
      statusMessage.value = 'Done!'
      break
    } else if (data.status === 'ERROR') {
      isProcessing.value = false
      statusMessage.value = 'Error during ML processing!'
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
  results.value = []
  
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

<style scoped>
.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  font-family: system-ui, -apple-system, sans-serif;
}
.upload-section {
  margin: 2rem 0;
  padding: 2rem;
  border: 2px dashed #ccc;
  border-radius: 8px;
  text-align: center;
}
.actions {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}
button {
  padding: 0.5rem 1rem;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}
button:disabled {
  background: #ccc;
  cursor: not-allowed;
}
select {
  padding: 0.5rem;
  border-radius: 4px;
  font-size: 1rem;
}
.status {
  padding: 1rem;
  background: #f0f8ff;
  border-radius: 4px;
  margin-bottom: 2rem;
  font-weight: bold;
}
.frames-grid {
  display: flex;
  gap: 1rem;
  overflow-x: auto;
  padding-bottom: 1rem;
}
.frame-img {
  height: 100px;
  border-radius: 4px;
  object-fit: cover;
}
.results-section {
  background: #f9f9f9;
  padding: 1.5rem;
  border-radius: 8px;
  margin-top: 2rem;
}
</style>
