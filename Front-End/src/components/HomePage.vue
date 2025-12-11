<template>
    <div class="video-container">
      <h2>Streamed Video</h2>
  
      <div v-if="videoUrl">
        <video
          ref="video"
          :src="videoUrl"
          controls
          width="640"
          height="360"
          @timeupdate="updateProgress"
          @loadedmetadata="setDuration"
        ></video>
  
        <div class="progress-bar">
          <input
            type="range"
            min="0"
            :max="duration"
            step="0.1"
            v-model="currentTime"
            @input="seekVideo"
          />
          <div class="time">
            {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
          </div>
        </div>
      </div>
  
      <p v-else>Loading video...</p>
    </div>
  </template>
  
  <script>
  export default {
    name: 'VideoPlayer',
    data() {
      return {
        videoUrl: null,
        currentTime: 0,
        duration: 0,
      };
    },
    mounted() {
      this.videoUrl = 'http://localhost:5000/stream/video';
    },
    methods: {
      updateProgress() {
        const video = this.$refs.video;
        this.currentTime = video.currentTime;
      },
      setDuration() {
        const video = this.$refs.video;
        this.duration = video.duration;
      },
      seekVideo() {
        const video = this.$refs.video;
        video.currentTime = this.currentTime;
      },
      formatTime(seconds) {
        const min = Math.floor(seconds / 60);
        const sec = Math.floor(seconds % 60);
        return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
      },
    },
  };
  </script>
  
  <style scoped>
  .video-container {
    text-align: center;
    padding: 20px;
  }
  
  video {
    border: 2px solid #ccc;
    border-radius: 8px;
  }
  
  .progress-bar {
    margin-top: 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  
  input[type="range"] {
    width: 640px;
  }
  
  .time {
    margin-top: 5px;
    font-size: 14px;
    color: #555;
  }
  </style>
  