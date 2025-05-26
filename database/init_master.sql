-- UALFlix Database Initialization - PASSWORD HASH CORRIGIDO
-- Script SQL com passwords hash mais pequenos

-- Create users table com password hash maior
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) DEFAULT '',
    password VARCHAR(255) NOT NULL,  -- CORRIGIDO: aumentado de 128 para 255
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create videos table
CREATE TABLE IF NOT EXISTS videos (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    filename VARCHAR(500),
    url VARCHAR(500),
    duration INTEGER,
    file_path VARCHAR(500),
    thumbnail_path VARCHAR(500),
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    view_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    user_id INTEGER REFERENCES users(id)
);

-- Create video_views table
CREATE TABLE IF NOT EXISTS video_views (
    id SERIAL PRIMARY KEY,
    video_id INTEGER REFERENCES videos(id),
    user_id INTEGER REFERENCES users(id),
    view_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    watch_duration INTEGER DEFAULT 0
);

-- Create replication test table
CREATE TABLE IF NOT EXISTS replication_test (
    id SERIAL PRIMARY KEY,
    test_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    test_data TEXT
);

