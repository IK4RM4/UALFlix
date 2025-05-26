-- database/init_master.sql
-- Inicialização do Master Database

-- Criar usuário de replicação
CREATE USER replica_user REPLICATION LOGIN ENCRYPTED PASSWORD 'replica_password';

-- Criar diretório de archive se não existir
\! mkdir -p /var/lib/postgresql/archive

-- Configurar permissões
GRANT CONNECT ON DATABASE ualflix TO replica_user;

-- Criar tabelas principais se não existirem
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS videos (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    duration INTEGER,
    file_path VARCHAR(500),
    thumbnail_path VARCHAR(500),
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    view_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS video_views (
    id SERIAL PRIMARY KEY,
    video_id INTEGER REFERENCES videos(id),
    user_id INTEGER REFERENCES users(id),
    view_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    watch_duration INTEGER DEFAULT 0
);

-- Inserir dados de teste
INSERT INTO users (username, email, password_hash, is_admin) VALUES 
('admin', 'admin@ualflix.com', 'hashed_password_123', TRUE),
('user1', 'user1@ualflix.com', 'hashed_password_456', FALSE)
ON CONFLICT (username) DO NOTHING;

INSERT INTO videos (title, description, duration, file_path, view_count) VALUES 
('Sample Video 1', 'First sample video for testing', 120, '/videos/sample1.mp4', 45),
('Sample Video 2', 'Second sample video for testing', 180, '/videos/sample2.mp4', 23),
('Sample Video 3', 'Third sample video for testing', 90, '/videos/sample3.mp4', 67)
ON CONFLICT DO NOTHING;

-- Mostrar status da replicação
SELECT 
    application_name,
    client_addr,
    state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn,
    sync_state
FROM pg_stat_replication;