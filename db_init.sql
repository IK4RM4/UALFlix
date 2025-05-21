-- Criar tabelas se não existirem
CREATE TABLE IF NOT EXISTS videos (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    filename TEXT NOT NULL,
    url TEXT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Adicionar restrição única para a coluna username
ALTER TABLE users ADD CONSTRAINT users_username_key UNIQUE (username);

-- Inserir utilizador admin predefinido (password: admin123)
INSERT INTO users (username, password, is_admin)
VALUES ('admin', 
        '$2b$12$QYDlQCYFqFxMXpXH9JLdVegHrfHPXWnUZFQEawzWTdC0g4CZJDwYy', -- Hash da password 'admin123'
        TRUE)
ON CONFLICT (username) DO NOTHING;

-- Inserir utilizador normal predefinido (password: user123)
INSERT INTO users (username, password, is_admin)
VALUES ('user', 
        '$2b$12$JF/XTeGJvCDwBXbJn95pIe8nj9QGxyqhAjC3Fir1HOwoJLkG9EYu.', -- Hash da password 'user123'
        FALSE)
ON CONFLICT (username) DO NOTHING;

-- Inserir alguns vídeos de exemplo
INSERT INTO videos (title, description, filename, url)
VALUES 
('Introdução ao UALFlix', 
 'Vídeo de demonstração da plataforma UALFlix', 
 'intro_ualflix.mp4',
 '/videos/intro_ualflix.mp4'),
 
('Tutorial de Docker', 
 'Aprenda a usar Docker para desenvolvimento e deploy de aplicações', 
 'docker_tutorial.mp4',
 '/videos/docker_tutorial.mp4'),
 
('Microserviços com Python', 
 'Como desenvolver arquiteturas de microserviços usando Python e Flask', 
 'microservices_python.mp4',
 '/videos/microservices_python.mp4')
ON CONFLICT DO NOTHING;