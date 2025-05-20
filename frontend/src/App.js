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
  const [systemStatus, setSystemStatus] = useState({
    services: [],
    isAdmin: false,
    loading: true,
  });

  const onLogin = async (e) => {
    e.preventDefault();
    const response = await api.post("/login", {
      username,
      password,
    });
    const data = await response.json();
    setAuthenticated(data.authenticated);
  };

  const onRegister = async (e) => {
    e.preventDefault();
    const response = await api.post("/register", {
      username,
      password,
    });
    const data = await response.json();
    console.log(data);
    setAuthenticated(data.authenticated);
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
        <div>
          <h1>Login</h1>
          <form>
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button onClick={onLogin}>Login</button>
            <button onClick={onRegister}>Register</button>
          </form>
        </div>
      )}
    </>
  );
}

export default App;
