<template>
  <div v-if="isVisible" class="modal-overlay" @click.self="closeModal">
    <div class="container">
      <div class="card">
        <span class="close-button" @click="$emit('close')">&times;</span>
        <h2>Profile</h2>
        <form @submit.prevent="validateAndUpdateProfile">
          <div class="scrollable">
            
            <label for="name">Name</label>
            <input type="text" id="name" v-model="profile.name" :disabled="isDisabled" @input="clearError('name')" required/>
            <span v-if="errors.name" class="error">{{ errors.name }}</span>

            <label for="email">Email</label>
            <input type="text" id="email" v-model="profile.email" disabled />

            <label for="role">Role</label>
            <select id="role" v-model="profile.role" disabled>
              <option value="" disabled>Role</option>
              <option v-for="role in roles" :key="role" :value="role">{{ role }}</option>
            </select>
          </div>

          <button type="submit" class="button" :disabled="isDisabled || hasErrors">Update Profile</button>
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
      profile: JSON.parse(localStorage.getItem('user')),
      roles: [
        'student', 'support_staff', 'admin'],
      errors: {
        name: ''
      }
    };
  },
  props: {
    isVisible: {
      type: Boolean,
      default: false
    }
  },
  computed: {
    isDisabled() {
      return this.profile.role === 'admin';
    },
    hasErrors() {
      return Object.values(this.errors).some(error => error);
    }
  },
  methods: {
    closeModal() {
      this.$emit('close');
    },
    validateAndUpdateProfile() {
      if (!this.profile.name) {
        this.errors.name = 'Name is required.';
      }
      if (!this.hasErrors) {
        this.updateProfile();
      }
    },
    async updateProfile() {
      try {
        const updateData = {
          name: this.profile.name
        };
        const response = await api.put('/profile', updateData);
        // Update local storage after successful update
        localStorage.setItem('user', JSON.stringify(this.profile));
        // Handle success
        console.log('Profile updated successfully:', response.data);
        this.$emit('close'); // Close the modal after successful update
      } catch (error) {
        console.error('Error updating profile:', error);
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
