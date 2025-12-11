<template>
  <div class="body">
    <nav>
      <div class="nav-left">
        <router-link to="/" class="nav-link">Home</router-link>
      </div>
    </nav>

    <div class="login-container">
      <div class="imgbox">
        <img src="@/assets/photo.svg" alt="Background Image">
      </div>

      <div class="contentbox registerContentbox">
        <div class="formbox card">
          <h2>Register</h2>
          <form @submit.prevent="validateForm">
            <div class="scrollable">
              <div class="inputbox">
                <label for="name">Name:</label>
                <input type="text" id="name" v-model="form.name" required>
                <span v-if="errors.name" class="error-message">{{ errors.name }}</span>
              </div>
              <div class="inputbox">
                <label for="email">Email:</label>
                <input type="email" id="email" v-model="form.email" required>
                <span v-if="errors.email" class="error-message">{{ errors.email }}</span>
              </div>
              <div class="inputbox">
                <label for="password">Password:</label>
                <input type="password" id="password" v-model="form.password" required>
                <span v-if="errors.password" class="error-message">{{ errors.password }}</span>
              </div>
              <div class="inputbox">
                <label for="retypePassword">Confirm Password:</label>
                <input type="password" id="retype-password" v-model="form.retypePassword" required>
                <span v-if="errors.retypePassword" class="error-message">{{ errors.retypePassword }}</span>
              </div>
              <div class="inputbox">
                <label for="role">Role:</label>
                <select id="role" v-model="form.role" required>
                  <option disabled value="">Role</option>
                  <option value="student">Student</option>
                  <option value="support_staff">Support Staff</option>
                </select>
                <span v-if="errors.role" class="error-message">{{ errors.role }}</span>
              </div>
            </div>
            <div class="inputbox">
              <input type="submit" value="Register">
            </div>
            <div class="inputbox">
              <p>Already have an account...? <router-link to="/login">Log In</router-link></p>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      form: {
        name: '',
        email: '',
        password: '',
        retypePassword: '', 
        role: '' 
      },
      errors: {}
    };
  },
  methods: {
    validateForm() {
      this.errors = {};

      // Field-specific validations
      if (!this.form.name) {
        this.errors.name = 'Name is required.';
      }
      if (!this.form.email) {
        this.errors.email = 'Email is required.';
      }
      if (!this.form.password) {
        this.errors.password = 'Password is required.';
      }
      if (!this.form.retypePassword) {
        this.errors.retypePassword = 'Please confirm your password.';
      }
      if (!this.form.role) {
        this.errors.role = 'Role is required.';
      }

      // Password confirmation validation
      if (this.form.password !== this.form.retypePassword) {
        this.errors.retypePassword = 'Passwords do not match.';
      }
      
      // Email validation for username
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailPattern.test(this.form.email)) {
        this.errors.email = 'Please enter a valid email address.';
      }

      // Password validation
      const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$/;
      if (!passwordPattern.test(this.form.password)) {
        this.errors.password = 'Password must be at least 8 characters long and include at least one uppercase letter, one lowercase letter, one digit, and one special character.';
      }

      if (Object.keys(this.errors).length === 0) {
        // Submit form if no validation errors
        this.registerUser();
      }
    },
    async registerUser() {
      try {
        const response = await axios.post('http://127.0.0.1:5000/register', {
          email: this.form.email,
          password: this.form.password,
          retypePassword: this.form.retypePassword,
          name: this.form.name,
          role: this.form.role,
        });

        const { user, access_token, refresh_token, message } = response.data;
        
        alert(message);

        // Store tokens in localStorage
        localStorage.setItem('user', JSON.stringify(user));
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', refresh_token);
        
        // Redirect to dashboard or another route
        if (user.role === 'student') {
          this.$router.push(`/student/dashboard/${user.name}`);
        } else if (user.role === 'support_staff') {
          this.$router.push(`/support_staff/dashboard/${user.name}`);
        } else if (user.role === 'admin') {
          this.$router.push(`/admin/dashboard/${user.name}`);
        }
        
      } catch (error) {
        if (error.response && error.response.data) {
          this.errors.email = error.response.data.error || 'An error occurred during registration.';
        } else {
          this.errors.email = 'An unexpected error occurred.';
        }
      }
    }
  }
};
</script>

<style scoped>
@import '@/assets/navBar.css';
@import '@/assets/loginRegister.css';
</style>
