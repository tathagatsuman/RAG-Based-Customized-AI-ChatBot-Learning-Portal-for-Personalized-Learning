<template>
  <nav>
    <!-- Hamburger Icon for Mobile -->
    <div class="hamburger" @click="toggleMenu">
      <span :class="{ 'hamburger-open': isMenuOpen }"></span>
      <span :class="{ 'hamburger-open': isMenuOpen }"></span>
      <span :class="{ 'hamburger-open': isMenuOpen }"></span>
    </div>

    <!-- Navigation Links -->
    <div :class="['nav-links', { 'show-menu': isMenuOpen }]">
      <div class="nav-left">
        <span @click="openModal" class="nav-link">Profile</span>
        <ProfileForm :isVisible="isProfileVisible" @close="isProfileVisible = false"  @updateCourses="fetchData"/>

        <router-link v-if="user.role === 'admin'" :to="{ name: 'adminDashboard', params: { name: user.name } }" class="nav-link" @click="closeMenu">Dashboard</router-link>
        <router-link v-if="user.role === 'student'" :to="{ name: 'studentDashboard', params: { name: user.name } }" class="nav-link" @click="closeMenu">Dashboard</router-link>
        <router-link v-if="user.role === 'support_staff'" :to="{ name: 'support_staffDashboard', params: { name: user.name } }" class="nav-link" @click="closeMenu">Dashboard</router-link>

        <span v-if="user.role === 'student'" @click="openEnrollmentForm" class="nav-link">Enroll new Course</span>
        <EnrollmentForm :isVisible="isEnrollmentFormVisible" :courses="courses" @close="isEnrollmentFormVisible = false" />

        <span v-if="user.role === 'support_staff'" @click="openInstructorForm" class="nav-link">Apply for Instructor</span>
        <InstructorForm :isVisible="isInstructorFormVisible" :courses="courses" @close="isInstructorFormVisible = false" />

        <span v-if="user.role === 'admin'" @click="openAddCourse" class="nav-link">Add new Course</span>
        <AddNewCourseForm :isVisible="isAddNewCourseVisible" @close="isAddNewCourseVisible = false" @updateCourses="fetchData"/>

        <span v-if="user.role === 'admin'" @click="openAddCourseContent" class="nav-link">Add Course Contents</span>
        <AddCourseContents :isVisible="isAddCourseContentVisible" @close="isAddCourseContentVisible = false" />
      </div>
      <div class="nav-right">
        <span @click="logoutHandler" class="nav-link">Log Out</span>
      </div>
    </div>
  </nav>
</template>

<script>
import ProfileForm from "@/components/icons/ProfileForm.vue";
import EnrollmentForm from "@/components/icons/EnrollmentForm.vue";
import InstructorForm from "@/components/icons/InstructorForm.vue";
import AddNewCourseForm from "@/components/icons/AddNewCourseForm.vue";
import AddCourseContents from "@/components/icons/AddCourseContents.vue";
import { logout } from "@/utils/logout";

export default {
  name: "NavBar",
  props: {
  courses: {
    type: Array
  }
},
  components: { ProfileForm, EnrollmentForm, InstructorForm, AddNewCourseForm, AddCourseContents },
  data() {
    return {
      user: JSON.parse(localStorage.getItem("user")) || {},
      isProfileVisible: false, 
      isInstructorFormVisible: false,
      isEnrollmentFormVisible: false,
      isAddNewCourseVisible: false,
      isAddCourseContentVisible: false,
      isMenuOpen: false,
    };
  },
  methods: {
    openModal() {
      this.isProfileVisible = true;
    },
    openEnrollmentForm() {
      this.isEnrollmentFormVisible = true;
    },
    openInstructorForm() {
      this.isInstructorFormVisible = true;
    },
    openAddCourse() {
      this.isAddNewCourseVisible = true;
    },
    openAddCourseContent() {
      this.isAddCourseContentVisible = true;
    },
    async logoutHandler() {
      try {
        await logout();
      } catch (error) {
        console.error("Error during logout:", error);
      }
    },
    toggleMenu() {
      this.isMenuOpen = !this.isMenuOpen;
    },
    closeMenu() {
      this.isMenuOpen = false;
    },
    fetchData() {
      this.$emit("fetchData");
    }
  },
};
</script>

<style scoped>
@import "@/assets/navBar.css";
</style>
