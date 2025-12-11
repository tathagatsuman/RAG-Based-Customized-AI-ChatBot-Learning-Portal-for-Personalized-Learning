<template>
    <div v-if="isVisible" class="modal-overlay" @click.self="closeModal">
      <div class="container">
        <div class="card">
          <span class="close-button" @click="$emit('close')">&times;</span>
          <h2>{{ isUpdation ? 'Update' : 'Add' }} Question</h2>
          <div class="scrollable">
            <form @submit.prevent="submitQuestion">
              <label for="question_text">Question Text</label>
              <textarea id="question_text" v-model="form.question_text" required></textarea>
              
              <label for="question_type">Question Type</label>
              <select id="question_type" v-model="form.question_type" required>
                <option value="" disabled>Select Question Type</option>
                <option value="mcq">MCQ</option>
                <option value="string">String</option>
              </select>
              
              <label v-if="form.question_type === 'mcq'" for="choices">Choices (comma-separated)</label>
              <input v-if="form.question_type === 'mcq'" type="text" id="choices" v-model="form.choices" />
              
              <label for="correct_answer">Correct Answer</label>
              <input type="text" id="correct_answer" v-model="form.correct_answer" required />
              
              <button type="submit" class="button">{{ isUpdation ? 'Update' : 'Submit' }}</button>
            </form>
          </div>
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
      isUpdation: {
        type: Boolean,
        default: false
      },
      assignmentId: {
        type: Number,
        default: null
      },
      questionData: {
        type: Object,
        default: () => ({})
      }
    },
    data() {
      return {
        form: {
          question_text: '',
          question_type: '',
          choices: '',
          correct_answer: ''
        }
      };
    },
    watch: {
      questionData: {
        handler(newVal) {
          if (this.isUpdation && newVal) {
            this.form.question_text = newVal.question_text || '';
            this.form.question_type = newVal.question_type || 'mcq';
            this.form.choices = newVal.choices ? newVal.choices.join(', ') : '';
            this.form.correct_answer = newVal.correct_answer || '';
          }
        },
        immediate: true
      }
    },
    methods: {
      closeModal() {
        this.$emit('close');
      },
      async submitQuestion() {
        try {
          if (this.isUpdation) {
            await api.put(`/update_assignment_question/${this.questionData.question_id}`, this.form);
            alert('Question updated successfully!');
          } else {
            await api.post(`/add_new_assignment_question/${this.assignmentId}`, this.form);
            alert('Question added successfully!');
          }
          this.closeModal();
          this.$emit('refresh');
        } catch (error) {
          alert('Error: ' + (error.response?.data?.error || error.message));
        }
      }
    }
  };
  </script>
  
  <style scoped>
  @import '@/assets/overlay.css';
  </style>
  