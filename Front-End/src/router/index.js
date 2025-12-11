import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '@/components/HomePage.vue';
import LoginPage from '@/components/LoginPage.vue';
import RegisterPage from '@/components/RegisterPage.vue';
import AdminDashboardPage from '@/components/AdminDashboardPage.vue';
import SupportStaffDashboardPage from '@/components/SupportStaffDashboardPage.vue';
import StudentDashboardPage from '@/components/StudentDashboardPage.vue';
import CourseContentPage from '@/components/CourseContentPage.vue';
import NotFound from '@/components/NotFound.vue';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL || '/'),
  routes: [
    { path: '/', component: HomePage, name: 'home' },
    { path: '/login', component: LoginPage, name: 'login' },
    { path: '/register', component: RegisterPage, name: 'register' },
    { path: '/admin/dashboard/:name', component: AdminDashboardPage, name:'adminDashboard', meta: { requiresAuth: true, role: 'admin' }, },
    { path: '/support_staff/dashboard/:name', component: SupportStaffDashboardPage, name: 'support_staffDashboard', meta: { requiresAuth: true, role: 'support_staff' } },
    { path: '/student/dashboard/:name', component: StudentDashboardPage, name: 'studentDashboard', meta: { requiresAuth: true, role: 'student' } },
    { path: '/course/content/:name', component: CourseContentPage, name: 'courseContent', meta: { requiresAuth: true } },
    { path: '/:pathMatch(.*)*', component: NotFound, name: 'NotFound' }
  ]
});

router.beforeEach((to, from, next) => {
  const user = JSON.parse(localStorage.getItem('user')) || {};
  const isLoggedIn = !!localStorage.getItem('access_token');
  const userRole = user.role;

  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!isLoggedIn) {
      return next({ name: 'Login' });
    }

    if (to.meta.role && to.meta.role !== userRole) {
      return next({ name: `${userRole}Dashboard`, params: { name: user.name } });
    }
  }

  next();
});

export default router

