import axios from 'axios';

export const logout = async () => {
    const accessToken = localStorage.getItem('access_token');
    const refreshToken = localStorage.getItem('refresh_token');

    try {
      // Attempt to log out using the access token
      if (accessToken) {
        await axios.post('http://127.0.0.1:5000/logout', {}, {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`
          }
        });
      }
    } catch (error) {
      // Handle case where access token is already expired
      if (error.response && error.response.status === 401) {
        console.error('Access token expired:', error);
      } else {
        console.error('Error during logout with access token:', error);
      }
    }

    // Proceed to log out using the refresh token, even if access token logout fails
    try {
      if (refreshToken) {
        await axios.post('http://127.0.0.1:5000/logout_refresh', {}, {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${refreshToken}`
          }
        });
      }
    } catch (error) {
      console.error('Error during logout with refresh token:', error);
    }

  handleLogout();
}

  // Handle logout process and clean up
const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  
    // Redirect to login page
    window.location.href = '/';
  };