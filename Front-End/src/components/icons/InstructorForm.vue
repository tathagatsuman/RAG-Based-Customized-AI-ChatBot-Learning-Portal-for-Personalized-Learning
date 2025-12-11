<template>
  <div v-if="isVisible" class="modal-overlay" @click.self="closeInstructorForm">
    <div class="container">
      <div class="card">
        <span class="close-button" @click="$emit('close')">&times;</span>
        <h2>Become Support Staff!</h2>

        <form @submit.prevent="applySupportStaff">
          <div class="scrollable">  
            <label for="course">Course</label>
            <select id="course" v-model="selectedCourse" required>
              <option value="" disabled>Select a Course</option>
              <option v-for="course in courses" :key="course.id" :value="course.id">
                {{ course.name }}
              </option>
            </select>
          </div>
          <button type="submit" class="button">Apply</button>
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
    closeInstructorForm() {
      this.$emit("close");
    },
    async applySupportStaff() {
      try {
        if (!this.selectedCourse) {
          alert("Please select a course");
          return;
        }

        const response = await api.post("/apply/support_staff", { course_id: this.selectedCourse });
        this.selectedCourse = "";
        console.log("Application successful:", response.data);
        alert(response.data.message);
        this.$emit("updateCourses");
        this.closeInstructorForm();
      } catch (error) {
        console.error("Error applying for support staff:", error);
        this.selectedCourse = "";
        alert(error.response?.data?.error || "Failed to apply for support staff.");
        this.closeInstructorForm();
      }
    },
  }
};
</script>

<style scoped>
@import '@/assets/overlay.css';
</style>
