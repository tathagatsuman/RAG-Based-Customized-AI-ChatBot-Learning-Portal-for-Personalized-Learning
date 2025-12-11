<template>
  <div v-if="isVisible" class="modal-overlay" @click.self="closeEnrollmentForm">
    <div class="container">
      <div class="card">
        <span class="close-button" @click="closeEnrollmentForm">&times;</span>
        <h2>Enroll for a New Course!</h2>

        <form @submit.prevent="EnrollCourse">
          <div class="scrollable">  
            <label for="course">Course</label>
            <select id="course" v-model="selectedCourse" required>
              <option value="" disabled>Select a Course</option>
              <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.name }}</option>
            </select>
          </div>
          <button type="submit" class="button">Enroll</button>
        </form>
        
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/utils/auth';

export default {
  props: {
    isVisible: {
      type: Boolean,
      required: true
    },
    courses: {
    type: Array,
    required: true 
  }
  },
  data() {
    return {
      selectedCourse: "",
    };
  },
  methods: {
    closeEnrollmentForm() {
      this.$emit("close");
    },
    async EnrollCourse() {
      try {
        if (!this.selectedCourse) {
          alert("Please select a course");
          return;
        }

        const response = await api.post('/register/course', { course_id: this.selectedCourse });
        this.selectedCourse = "";
        alert(response.data.message);
        
        // Emit event to refresh courses in dashboard
        this.$emit("updateCourses");

        this.closeEnrollmentForm();
      } catch (error) {
        console.error("Error enrolling in course:", error.response?.data || error);
        this.selectedCourse = "";
        alert(error.response?.data?.error || "Failed to enroll in the course.");
        this.closeEnrollmentForm();
      }
    },
  }
};
</script>

<style scoped>
@import '@/assets/overlay.css';
</style>
