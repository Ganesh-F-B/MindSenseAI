import axios from 'axios';
import Cookies from 'js-cookie';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000',
});

api.interceptors.request.use((config) => {
  const token =
    Cookies.get('token') ||
    (typeof window !== 'undefined' ? window.localStorage.getItem('token') : null);

  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

export default api;
