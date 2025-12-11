<template>
    <div v-if="isVisible" class="modal-overlay" @click.self="closeAddCourseContents">
      <div class="container">
        <div class="card">
          <span class="close-button" @click="$emit('close')">&times;</span>
          <h2>Add Course Content</h2>
          <div class="scrollable">
          
          <form @submit.prevent="submitCourseContent">
            
              
              <label for="course_id">Course ID</label>
              <input type="number" id="course_id" v-model="form.course_id" required :disabled="isUpdation"/>
  
              <label for="week">Week</label>
              <input type="number" id="week" v-model="form.week" min="1" max="52" required :disabled="isUpdation"/>
              
              <label for="title">Title</label>
              <input type="text" id="title" v-model="form.title" required :disabled="isUpdation"/>
  
              <label for="description">Description</label>
              <textarea id="description" v-model="form.description" required></textarea>
  
              <label for="video_link">Video Link</label>
              <input type="url" id="video_link" v-model="form.video_link" required />
              
            
            <button type="submit" class="button">Submit</button>
          </form>
          
          <!-- Hide Upload CSV if updating -->
          <div v-if="!isUpdation">
            <h3>OR Upload CSV</h3>
            <input type="file" @change="handleFileUpload" accept=".csv" />
            <button @click="uploadCSV" type="submit" class="button">Upload CSV</button>
          </div>
        </div>
        </div>
      </div>
    </div>
  </template>
  
  <script>
  import api from '@/utils/auth';
  
  export default {
    data() {
      return {
        form: {
          course_id: this.$route.query.id || '',
          week: '',
          title: '',
          description: '',
          video_link: ''
        },
        csvFile: null
      };
    },
    props: {
      isVisible: {
        type: Boolean,
        required: true
      },
      isUpdation: {
        type: Boolean,
        default: false
      },
      contentData: {
        type: Object,
        default: () => ({})
      }
    },
    watch: {
        contentData: {
        handler(newVal) {
            if (newVal) {
            this.form.week = newVal.week || '';
            this.form.title = newVal.title || '';
            this.form.description = newVal.description || '';
            this.form.video_link = newVal.video_link || '';
            }
        },
        immediate: true
        }
    },
    methods: {
      closeAddCourseContents() {
        this.$emit('close');
      },
      async submitCourseContent() {
        try {
          await api.post('/add_or_update/course_contents', this.form);
          alert('Course content added successfully!');
          this.form.course_id = '';
          this.form.week = '';
          this.form.title = '';
          this.form.description = '';
          this.form.video_link = '';
          this.closeAddCourseContents();
          this.$emit("refresh");
        } catch (error) {
          alert('Error adding course content: ' + error.response.data.error);
          this.form.course_id = '';
          this.form.week = '';
          this.form.title = '';
          this.form.description = '';
          this.form.video_link = '';
          this.closeAddCourseContents();
        }
      },
      handleFileUpload(event) {
        this.csvFile = event.target.files[0];
      },
      async uploadCSV() {
        if (!this.csvFile) {
          alert('Please select a CSV file.');
          return;
        }
        
        const formData = new FormData();
        formData.append('file', this.csvFile);
        
        try {
          await api.post('/upload_course_contents', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
          alert('CSV uploaded successfully!');
          this.csvFile = null
          this.closeAddCourseContents();
          this.$emit("refresh");
        } catch (error) {
          alert('Error uploading CSV: ' + error.response.data.error);
          this.csvFile = null
          this.closeAddCourseContents()
        }
      }
    }
  };
  </script>
  
  <style scoped>
  @import '@/assets/overlay.css';
  </style>
  