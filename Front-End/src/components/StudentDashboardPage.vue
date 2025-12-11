<template>
  <div class="body">
    <NavBar :courses="courses" @fetchData="fetchData"/>
    <div class="container">
      <h2>Welcome! {{ user.name }}</h2>

      <!-- Registered Courses Section -->
      <div class="card cardBack mt-6">
        <h2 class="text-2xl font-bold text-center mb-4">Registered Courses</h2>
        <div v-if="enrolled_courses.length > 0" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          <div v-for="course in enrolled_courses" :key="course.id" class="card" @click="goToCourse(course)">
            <h2 class="text-xl font-bold">{{ course.name }}</h2>
            <p class="text-gray-600">{{ course.description }}</p>
          </div>
        </div>
        <p v-else class="text-center text-gray-500">No enrolled courses found.</p>
      </div>
    </div>

    <!-- Floating Chatbot Button -->
    <div class="chat-container">
      <button @click="toggleChat" class="chat-button">
        💬
        <span class="tooltip">Chat with AI Chatbot</span>
      </button>
    </div>
    <!-- Chatbot Overlay -->
    <ChatBot v-if="chatOpen" @closeChat="toggleChat" />
  </div>
</template>

<script>
import api from '@/utils/auth';
import NavBar from '@/components/icons/NavBar.vue';
import ChatBot from '@/components/ChatBot.vue';

export default {
  name: "StudentDashboard",
  components: { NavBar, ChatBot },
  data() {
    return {
      user: JSON.parse(localStorage.getItem('user')) || { name: "Student" },
      courses: [],
      enrolled_courses: [],
      chatOpen: false,
    };
  },
  methods: {
    async fetchData() {
      try {
        const response = await api.get('/dashboard/student');
        this.courses = response.data.courses;
        this.enrolled_courses = response.data.enrolled_courses;
        console.log(response)
      } catch (error) {
        console.error("Error fetching dashboard data:", error);
      }
    },
    goToCourse(course) {
      this.$router.push({ name: "courseContent", query: { id: course.id, name: course.name }});
    },
    toggleChat() {
      this.chatOpen = !this.chatOpen;
    }
  },
  created() {
    this.fetchData();
  },
};
</script>

<style scoped>
@import '@/assets/dashboardBody.css';
@import '@/assets/card.css';

.cardBack {
    background: linear-gradient(90deg, #667eea, #764ba2);
}

.chat-container {
  position: fixed;
  bottom: 50px;
  right: 50px;
}

.chat-button {
  background-color: black;
  color: white;
  padding: 15px;
  border-radius: 50%;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  position: relative;
  transition: background 0.3s ease-in-out;
}

.chat-button:hover {
  background-color: #333;
}

.tooltip {
  visibility: hidden;
  background-color: #555;
  color: white;
  text-align: center;
  padding: 5px 10px;
  border-radius: 5px;
  position: absolute;
  bottom: 60px;
  right: 50%;
  transform: translateX(50%);
  white-space: nowrap;
  opacity: 0;
  transition: opacity 0.3s ease-in-out;
}

.chat-button:hover .tooltip {
  visibility: visible;
  opacity: 1;
}
</style>
