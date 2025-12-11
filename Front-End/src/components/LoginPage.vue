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

      <div class="contentbox">
        <div class="formbox card">
          <h2>Login</h2>
          <form @submit.prevent="validateForm">
            <div class="inputbox">
              <label for="email">Email</label>
              <input type="text" v-model="form.email" id="email" required>
              <span v-if="errors.email" class="error-message">{{ errors.email }}</span>
            </div>
            <div class="inputbox">
              <label for="password">Password</label>
              <input type="password" v-model="form.password" id="password" required>
              <span v-if="errors.password" class="error-message">{{ errors.password }}</span>
            </div>
            <div class="inputbox">
              <input type="submit" value="Sign in">
            </div>
            <div class="inputbox">
              <p>Don't have an account...? <router-link to="/register">Sign Up</router-link></p>
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
      email: '',
      password: ''
    },
    errors: {}
  };
},
methods: {
  validateForm() {
    this.errors = {};
    
    // Email validation
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!this.form.email) {
      this.errors.email = 'Email is required.';
    } else if (!emailPattern.test(this.form.email)) {
      this.errors.email = 'Please enter a valid email address.';
    }

    // Password validation
    const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$/;
    if (!this.form.password) {
      this.errors.password = 'Password is required.';
    } else if (!passwordPattern.test(this.form.password)) {
      this.errors.password = 'Password must be at least 8 characters long and include at least one uppercase letter, one lowercase letter, one digit, and one special character.';
    }

    if (Object.keys(this.errors).length === 0) {
      this.loginUser();
      console.log('Form submitted successfully');
    }
  },
  async loginUser() {
  try {
    const response = await axios.post('http://127.0.0.1:5000/login', {
      email: this.form.email,
      password: this.form.password
    });

    console.log('Login Response:', response.data); // Debugging line

    const { user, access_token, refresh_token, message } = response.data;

    console.log(message)

    if (!user || !access_token || !refresh_token) {
      console.error("Invalid response from the server");
      return;
    }

    localStorage.setItem('user', JSON.stringify(user));
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);

    console.log('User:', user);
    console.log('Redirecting...');

    if (user.role === 'student') {
      this.$router.push(`/student/dashboard/${user.name}`);
    } else if (user.role === 'support_staff') {
      this.$router.push(`/support_staff/dashboard/${user.name}`);
    } else if (user.role === 'admin') {
      this.$router.push(`/admin/dashboard/${user.name}`);
    }

  } catch (error) {
    console.error('Login Error:', error);
    if (error.response && error.response.data) {
      this.errors.server = error.response.data.error || 'Login failed. Please try again.';
    } else {
      this.errors.server = 'An error occurred. Please try again.';
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
