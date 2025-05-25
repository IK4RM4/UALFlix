import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 300000, // 5 minutos para uploads grandes
  maxContentLength: 1024 * 1024 * 1024, // 1GB
  maxBodyLength: 1024 * 1024 * 1024, // 1GB
});

// Interceptor para adicionar token em todas as requisições
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('sessionToken');
    if (token) {
      config.headers['X-Session-Token'] = token;
    }
    
    // Para uploads, aumentar o timeout
    if (config.data instanceof FormData) {
      config.timeout = 600000; // 10 minutos para uploads
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para lidar com respostas de erro de autenticação
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      // Token inválido ou expirado
      localStorage.removeItem('sessionToken');
      localStorage.removeItem('authenticated');
      localStorage.removeItem('username');
      localStorage.removeItem('user');
      
      // Redirecionar para login se não estiver já na página de login
      if (window.location.pathname !== '/') {
        window.location.reload();
      }
    }
    return Promise.reject(error);
  }
);

export default api;