<template>
  <div class="body">
    <NavBar @fetchData="fetchData"/>
    <div class="container">
      <h2>Welcome Admin! {{ user.name }}</h2>

      <!-- Pending Support Staff Approvals -->
      <div class="card mt-6">
        <h2 class="text-2xl font-bold">Pending Support Staff Approvals</h2>
        <div class="overflow-x-auto">
          <table class="w-[90%] mx-auto border-collapse border border-gray-300">
            <thead class="bg-gray-100">
              <tr>
                <th class="border border-gray-300 px-4 py-2">Name</th>
                <th class="border border-gray-300 px-4 py-2">Email</th>
                <th class="border border-gray-300 px-4 py-2">Course</th>
                <th class="border border-gray-300 px-4 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="staff in pendingApprovals" :key="staff.staff_id" class="hover:bg-gray-50">
                <td class="border border-gray-300 px-4 py-2">{{ staff.staff_name }}</td>
                <td class="border border-gray-300 px-4 py-2">{{ staff.staff_email }}</td>
                <td class="border border-gray-300 px-4 py-2">{{ staff.course_name }}</td>
                <td class="border border-gray-300 px-4 py-2">
                  <button @click="manageApprovals(staff.staff_id, staff.course_id, 'approve')" class="button">Approve</button>
                  <button @click="manageApprovals(staff.staff_id, staff.course_id, 'reject')" class="button">Reject</button>
                </td>
              </tr>
              <tr v-if="pendingApprovals.length === 0">
                <td colspan="4" class="border border-gray-300 px-4 py-2 text-center text-gray-600">No pending approvals.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Pending Student Enrollment Approvals -->
      <div class="card mt-6">
        <h2 class="text-2xl font-bold">Pending Student Enrollment Approvals</h2>
        <div class="overflow-x-auto">
          <table class="w-[90%] mx-auto border-collapse border border-gray-300">
            <thead class="bg-gray-100">
              <tr>
                <th class="border border-gray-300 px-4 py-2">Name</th>
                <th class="border border-gray-300 px-4 py-2">Email</th>
                <th class="border border-gray-300 px-4 py-2">Course</th>
                <th class="border border-gray-300 px-4 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="enrollment in pendingEnrollments" :key="enrollment.student_id" class="hover:bg-gray-50">
                <td class="border border-gray-300 px-4 py-2">{{ enrollment.student_name }}</td>
                <td class="border border-gray-300 px-4 py-2">{{ enrollment.student_email }}</td>
                <td class="border border-gray-300 px-4 py-2">{{ enrollment.course_name }}</td>
                <td class="border border-gray-300 px-4 py-2">
                  <button @click="manageEnrollments(enrollment.student_id, enrollment.course_id, 'approve')" class="button">Approve</button>
                  <button @click="manageEnrollments(enrollment.student_id, enrollment.course_id, 'reject')" class="button">Reject</button>
                </td>
              </tr>
              <tr v-if="pendingEnrollments.length === 0">
                <td colspan="4" class="border border-gray-300 px-4 py-2 text-center text-gray-600">No pending approvals.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- All Courses Section -->
      <div class="card cardBack mt-6">
        <h2 class="text-2xl font-bold text-center mb-4">All Courses</h2>
        <div v-if="courses.length > 0" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          <div v-for="course in courses" :key="course.id" class="card" @click="goToCourse(course)">
            <h2 class="text-xl font-bold">{{ course.name }}</h2>
            <p class="text-gray-600">{{ course.description }}</p>
          </div>
        </div>
        <p v-else class="text-center text-gray-500">No courses found.</p>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/utils/auth';
import NavBar from "@/components/icons/NavBar.vue";

export default {
  name: "AdminDashboard",
  components: { NavBar },
  data() {
    return {
      user: JSON.parse(localStorage.getItem('user')) || { name: "Admin" },
      pendingApprovals: [],
      pendingEnrollments: [],
      courses: [],
    };
  },
  methods: {
    async fetchData() {
      try {
        const response = await api.get('/dashboard/admin');
        Object.assign(this, response.data);
      } catch (error) {
        console.error("Error fetching dashboard data:", error);
      }
    },
    async manageEnrollments(student_id, course_id, action) {
      await api.put('/approve/course_enrollment', { student_id, course_id, action });
      this.fetchData();
    },
    async manageApprovals(staff_id, course_id, action) {
      await api.put('/approve/support_staffs', { staff_id, course_id, action });
      this.fetchData();
    },
    goToCourse(course) {
      this.$router.push({ name: "courseContent", query: { id: course.id, name: course.name }});
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
@import '@/assets/table.css';

.cardBack {
    background: linear-gradient(90deg, #667eea, #764ba2);
}

</style>
