import axios from 'axios';
import { logout } from '@/utils/logout';

const api = axios.create({
  baseURL: 'http://127.0.0.1:5000',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;
    
    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');

      if (refreshToken) {
        try {
          const { data } = await axios.post('http://127.0.0.1:5000/refresh', {}, {
            headers: { Authorization: `Bearer ${refreshToken}` }
          });

          localStorage.setItem('access_token', data.access_token);

          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          console.error('Refresh token failed:', refreshError);
          logout();
          return null;
        }
      } else {
        logout();
        return null;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
