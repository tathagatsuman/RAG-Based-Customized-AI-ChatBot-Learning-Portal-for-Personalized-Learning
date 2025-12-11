<template>
    <div class="not-found">
      <h1>404</h1>
      <p>Oops! The page you're looking for doesn't exist.</p>
      <router-link to="/">Go back to Home</router-link>
    </div>
  </template>
  
  <script>
  export default {
    name: 'NotFound',
  };
  </script>
  
  <style scoped>
  .not-found {
    text-align: center;
    padding: 50px;
  }
  
  .not-found h1 {
    font-size: 100px;
    margin: 0;
    color: #ff6347; /* Tomato color for emphasis */
  }
  
  .not-found p {
    font-size: 20px;
    margin: 20px 0;
  }
  
  .not-found a {
    font-size: 18px;
    color: #3498db;
    text-decoration: none;
    border: 2px solid #3498db;
    padding: 10px 20px;
    border-radius: 5px;
    transition: background-color 0.3s ease, color 0.3s ease;
  }
  
  .not-found a:hover {
    background-color: #3498db;
    color: #fff;
  }
  </style>
  