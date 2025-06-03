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
  const [user, setUser] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState(null);

  const saveSession = (token, userData) => {
    localStorage.setItem('sessionToken', token);
    localStorage.setItem('authenticated', 'true');
    localStorage.setItem('username', userData.username);
    localStorage.setItem('user', JSON.stringify(userData));
  };

  const clearSession = () => {
    localStorage.removeItem('sessionToken');
    localStorage.removeItem('authenticated');
    localStorage.removeItem('username');
    localStorage.removeItem('user');
  };

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
        setUser(response.data.user);
        saveSession(response.data.token, response.data.user);
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
        setAuthenticated(true);
        setUser(response.data.user);
        saveSession(response.data.token, response.data.user);
      } else {
        setLoginError(response.data.error || "Registo falhou");
      }
    } catch (err) {
      console.error("Erro de registo:", err);
      setLoginError(err.response?.data?.error || "Erro durante o registo. Por favor, tente novamente.");
    }
  };

  const onLogout = async () => {
    try {
      const token = localStorage.getItem('sessionToken');
      if (token) {
        await api.post("/auth/logout", { token });
      }
    } catch (err) {
      console.error("Erro ao fazer logout:", err);
    } finally {
      setAuthenticated(false);
      setUser(null);
      clearSession();
    }
  };

  const validateSession = async () => {
    const token = localStorage.getItem('sessionToken');
    const storedUser = localStorage.getItem('user');
    
    if (token && storedUser) {
      try {
        const response = await api.post("/auth/validate", { token });
        if (response.data.success) {
          setAuthenticated(true);
          setUser(response.data.user);
          setUsername(response.data.user.username);
        } else {
          clearSession();
        }
      } catch (err) {
        console.error("Erro ao validar sessão:", err);
        clearSession();
      }
    }
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

  // ✅ CORRIGIDO: isAdmin baseado apenas no user, não no sucesso da API
  const isUserAdmin = () => {
    return user && user.is_admin === true;
  };

  useEffect(() => {
    validateSession();
  }, []);

  useEffect(() => {
    if (authenticated) {
      fetchVideos();
    }
  }, [authenticated, user]);

  const handleVideoUpload = async (newVideoFilename) => {
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
                Todos os Vídeos
              </button>
              <button
                className={
                  activeTab === "my-videos" ? "nav-btn active" : "nav-btn"
                }
                onClick={() => setActiveTab("my-videos")}
              >
                Meus Vídeos
              </button>
              <button
                className={
                  activeTab === "upload" ? "nav-btn active" : "nav-btn"
                }
                onClick={() => setActiveTab("upload")}
              >
                Fazer Upload
              </button>
              {/* ✅ CORRIGIDO: Tab sempre visível se for admin */}
              {isUserAdmin() && (
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
                Sair ({user?.username})
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
                showUploader={true}
              />
            )}

            {activeTab === "my-videos" && (
              <VideoList
                videos={videos.filter(video => video.uploaded_by === user?.username)}
                loading={loading}
                error={error}
                onRefresh={fetchVideos}
                showUploader={true}
                title="Meus Vídeos"
              />
            )}

            {activeTab === "upload" && (
              <UploadVideo handleVideoUpload={handleVideoUpload} />
            )}

            {/* ✅ CORRIGIDO: Componente sempre renderiza se for admin */}
            {activeTab === "admin" && isUserAdmin() && (
              <SystemStatus />
            )}
          </main>

          <footer className="app-footer">
            <p>
              UALFlix - Projeto de Arquitetura Avançada de Sistemas - 2024/2025
            </p>
            <p>
              Utilizador: {user?.username} | 
              {user?.is_admin ? " Administrador" : " Utilizador"} | 
              Vídeos: {videos.length}
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
            <h3> Utilizadores de Demonstração - Fazer Registo</h3>
            <p><strong>Admin:</strong> username: admin, password: admin</p>
          
          </div>
          
        </div>
      )}
    </>
  );
}

export default App;