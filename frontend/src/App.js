import React, { useEffect, useState } from "react";
import api from "./api";
import "./App.css";
import SystemStatus from "./SystemStatus";
import UploadVideo from "./UploadVideo";
import VideoList from "./VideoList";

function App() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("videos");
  const [authenticated, setAuthenticated] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState(null);
  const [systemStatus, setSystemStatus] = useState({
    services: [],
    isAdmin: false,
    loading: true,
  });

  const onLogin = async (e) => {
    e.preventDefault();
    setLoginError(null);
    
    try {
      console.log("Tentando login para:", username);
      const response = await api.post("/auth/login", {
        username,
        password,
      });
      
      console.log("Resposta de login:", response.data);
      
      if (response.data.success) {
        setAuthenticated(true);
        localStorage.setItem('authenticated', 'true');
        localStorage.setItem('username', username);
      } else {
        setLoginError(response.data.error || "Login falhou");
      }
    } catch (err) {
      console.error("Erro de login:", err);
      setLoginError(err.response?.data?.error || "Erro durante o login. Por favor, tente novamente.");
    }
  };

  const onRegister = async (e) => {
    e.preventDefault();
    setLoginError(null);
    
    try {
      console.log("Tentando registar:", username);
      const response = await api.post("/auth/register", {
        username,
        password,
      });
      
      console.log("Resposta de registo:", response.data);
      
      if (response.data.success) {
        // Fazer login automaticamente após o registo bem-sucedido
        setAuthenticated(true);
        localStorage.setItem('authenticated', 'true');
        localStorage.setItem('username', username);
      } else {
        setLoginError(response.data.error || "Registo falhou");
      }
    } catch (err) {
      console.error("Erro de registo:", err);
      setLoginError(err.response?.data?.error || "Erro durante o registo. Por favor, tente novamente.");
    }
  };

  const onLogout = () => {
    setAuthenticated(false);
    localStorage.removeItem('authenticated');
    localStorage.removeItem('username');
  };

  const fetchVideos = async () => {
    setLoading(true);
    try {
      const response = await api.get("/videos");
      setVideos(response.data);
      setError(null);
    } catch (err) {
      console.error("Erro ao buscar vídeos:", err);
      setError(
        "Não foi possível carregar os vídeos. Tente novamente mais tarde."
      );
    } finally {
      setLoading(false);
    }
  };

  const fetchSystemStatus = async () => {
    try {
      // Verificar se o usuário tem acesso à área administrativa
      const adminCheck = await api.get("/admin/check");
      const isAdmin = adminCheck.data.isAdmin;

      if (isAdmin) {
        // Buscar status dos serviços
        const statusResponse = await api.get("/admin/services");
        setSystemStatus({
          services: statusResponse.data,
          isAdmin: true,
          loading: false,
        });
      } else {
        setSystemStatus({
          services: [],
          isAdmin: false,
          loading: false,
        });
      }
    } catch (err) {
      console.error("Erro ao verificar status do sistema:", err);
      setSystemStatus({
        services: [],
        isAdmin: false,
        loading: false,
        error: "Não foi possível carregar o status do sistema.",
      });
    }
  };

  useEffect(() => {
    // Verificar se o utilizador estava previamente autenticado
    const storedAuth = localStorage.getItem('authenticated');
    const storedUsername = localStorage.getItem('username');
    
    if (storedAuth === 'true' && storedUsername) {
      setAuthenticated(true);
      setUsername(storedUsername);
    }
    
    fetchVideos();
    fetchSystemStatus();
  }, []);

  const handleVideoUpload = async (newVideoFilename) => {
    // Atualiza a lista de vídeos após o upload
    await fetchVideos();
  };

  return (
    <>
      {authenticated ? (
        <div className="app-container">
          <header className="app-header">
            <h1>UALFlix 🎬</h1>
            <nav className="app-nav">
              <button
                className={
                  activeTab === "videos" ? "nav-btn active" : "nav-btn"
                }
                onClick={() => setActiveTab("videos")}
              >
                Vídeos
              </button>
              <button
                className={
                  activeTab === "upload" ? "nav-btn active" : "nav-btn"
                }
                onClick={() => setActiveTab("upload")}
              >
                Fazer Upload
              </button>
              {systemStatus.isAdmin && (
                <button
                  className={
                    activeTab === "admin" ? "nav-btn active" : "nav-btn"
                  }
                  onClick={() => setActiveTab("admin")}
                >
                  Administração
                </button>
              )}
              <button 
                className="nav-btn logout-btn" 
                onClick={onLogout}
              >
                Sair ({username})
              </button>
            </nav>
          </header>

          <main className="app-content">
            {activeTab === "videos" && (
              <VideoList
                videos={videos}
                loading={loading}
                error={error}
                onRefresh={fetchVideos}
              />
            )}

            {activeTab === "upload" && (
              <UploadVideo handleVideoUpload={handleVideoUpload} />
            )}

            {activeTab === "admin" && systemStatus.isAdmin && (
              <SystemStatus
                status={systemStatus}
                onRefresh={fetchSystemStatus}
              />
            )}
          </main>

          <footer className="app-footer">
            <p>
              UALFlix - Projeto de Arquitetura Avançada de Sistemas - 2024/2025
            </p>
          </footer>
        </div>
      ) : (
        <div className="login-container">
          <h1>UALFlix 🎬</h1>
          <h2>Login</h2>
          
          {loginError && (
            <div className="login-error">
              {loginError}
            </div>
          )}
          
          <form className="auth-form">
            <div className="form-group">
              <label htmlFor="username">Nome de utilizador</label>
              <input
                id="username"
                type="text"
                placeholder="Digite o seu nome de utilizador"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                placeholder="Digite a sua password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            
            <div className="auth-buttons">
              <button className="auth-btn login-btn" onClick={onLogin}>Entrar</button>
              <button className="auth-btn register-btn" onClick={onRegister}>Registar</button>
            </div>
          </form>
          
          <div className="demo-users">
            <h3>Utilizadores de demonstração:</h3>
            <p><strong>Admin:</strong> username: admin, password: admin123</p>
            <p><strong>User:</strong> username: user, password: user123</p>
          </div>
        </div>
      )}
    </>
  );
}

export default App;