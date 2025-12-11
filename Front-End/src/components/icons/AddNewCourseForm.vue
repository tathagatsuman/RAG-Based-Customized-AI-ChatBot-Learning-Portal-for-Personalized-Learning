<template>
  <div v-if="isVisible" class="modal-overlay" @click.self="closeAddCourse">
    <div class="container">
      <div class="card">
        <span class="close-button" @click="$emit('close')">&times;</span>
        <h2>Add New Course</h2>
        <form @submit.prevent="validateAndSubmit">
          <div class="scrollable">
            <label for="courseName">Course Name</label>
            <input type="text" id="courseName" v-model="course.name" @input="clearError('name')" required/>
            <span v-if="errors.name" class="error">{{ errors.name }}</span>

            <label for="professor">Professor Name</label>
            <input type="text" id="professor" v-model="course.prof" @input="clearError('prof')" required/>
            <span v-if="errors.prof" class="error">{{ errors.prof }}</span>
          </div>

          <button type="submit" class="button" :disabled="hasErrors">Add Course</button>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/utils/auth';

export default {
  data() {
    return {
      course: {
        name: '',
        prof: ''
      },
      errors: {}
    };
  },
  props: {
    isVisible: {
      type: Boolean,
      default: false
    }
  },
  computed: {
    hasErrors() {
      return Object.values(this.errors).some(error => error);
    }
  },
  methods: {
    closeAddCourse() {
      this.$emit('close');
    },
    validateAndSubmit() {
      this.errors = {};
      if (!this.course.name || this.course.name.length > 100) {
        this.errors.name = "Course name is required (max 100 characters).";
      }
      if (!this.course.prof || this.course.prof.length > 100) {
        this.errors.prof = "Professor name is required (max 100 characters).";
      }
      if (!this.hasErrors) {
        this.addCourse();
      }
    },
    async addCourse() {
      try {
        const response = await api.post('/add/new_course', this.course);
        console.log('Course added:', response.data);
        alert(response.data.message);
        this.course.name = "";
        this.course.prof = "";
        this.$emit("updateCourses");
        this.closeAddCourse();
      } catch (error) {
        console.error('Error adding course:', error.response?.data || error.message);
        this.course.name = "";
        this.course.prof = "";
        this.closeAddCourse();
      }
    },
    clearError(field) {
      this.errors[field] = '';
    }
  }
};
</script>

<style scoped>
@import '@/assets/overlay.css';
.error {
  color: red;
  font-size: 0.8em;
  margin-top: 4px;
}
</style>
