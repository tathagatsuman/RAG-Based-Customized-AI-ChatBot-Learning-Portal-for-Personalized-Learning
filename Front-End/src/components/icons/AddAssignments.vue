<template>
    <div v-if="isVisible" class="modal-overlay" @click.self="closeModal">
      <div class="container">
        <div class="card">
          <span class="close-button" @click="$emit('close')">&times;</span>
          <h2>Add Assignment</h2>
          <div class="scrollable">
            <form @submit.prevent="submitAssignment">
              <label for="course_id">Course ID</label>
              <input type="number" id="course_id" v-model="form.course_id" disabled required />
  
              <label for="week">Week</label>
              <input type="number" id="week" v-model="form.week" min="1" max="52" required />
  
              <label for="title">Title</label>
              <input type="text" id="title" v-model="form.title" required />
  
              <label for="due_date">Due Date</label>
              <input type="datetime-local" id="due_date" v-model="form.due_date" required />
  
              <!-- Hide Upload CSV if updating -->
                <div v-if="!isUpdation">
                <label for="csvUpload">Upload CSV:</label>
                <input type="file" id="csvUpload" @change="handleFileUpload" accept=".csv" />
                </div>
              
              <button type="submit" class="button">Submit</button>
            </form>
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
          week: "",
          title: "",
          due_date: "",
          assignment_id: ""
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
        required: true
      },
      assignmentData: {
        type: Object,
        default: () => ({})
      }
    },
    watch: {
        assignmentData: {
        handler(newVal) {
            if (newVal) {
            this.form.week = newVal.week || '';
            this.form.title = newVal.title || '';
            this.form.due_date = newVal.due_date || '';
            this.form.assignment_id = newVal.assignment_id || '';
            }
        },
        immediate: true
        }
    },
    methods: {
      closeModal() {
        this.$emit('close');
      },
      handleFileUpload(event) {
        this.csvFile = event.target.files[0];
      },
      async submitAssignment() {
        const formData = new FormData();
        formData.append('course_id', this.form.course_id);
        formData.append('week', this.form.week);
        formData.append('title', this.form.title);
        formData.append('due_date', this.formatDueDate(this.form.due_date));
        formData.append('file', this.csvFile);
        if (!this.isUpdation) {
            if (!this.csvFile) {
            alert('Please select a CSV file.');
            return;
            }   

            try {
                await api.post('/add_assignment/questions', formData);
                alert('Assignment added successfully!');
                this.$emit('refresh');
                this.resetForm();
                this.closeModal();
            } catch (error) {
                alert('Error: ' + (error.response?.data?.error || 'Unknown error'));
            }
        } else {
            try {
                await api.put(`/update_assignment/${this.assignmentData.assignment_id}`, formData);
                alert('Assignment updated successfully!');
                this.$emit('refresh');
                this.resetForm();
                this.closeModal();
            } catch (error) {
                alert('Error: ' + (error.response?.data?.error || 'Unknown error'));
            }
        }  
        

        
        
      },
      formatDueDate(dateTime) {
        const date = new Date(dateTime);
        return date.toISOString().slice(0, 19).replace('T', ' ');
      },
      resetForm() {
        this.form = { course_id: '', week: '', title: '', due_date: '' };
        this.csvFile = null;
      }
    }
  };
  </script>
  
  <style scoped>
  @import '@/assets/overlay.css';
  </style>
  