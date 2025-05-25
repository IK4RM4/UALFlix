-- Create users table with all required columns
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create videos table with all required columns
CREATE TABLE IF NOT EXISTS videos (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    filename VARCHAR(500) NOT NULL,  
    url VARCHAR(500),                 
    file_path VARCHAR(500),          
    thumbnail_path VARCHAR(500),
    duration INTEGER,
    file_size BIGINT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    genre VARCHAR(100),
    year INTEGER,
    rating DECIMAL(3,1),
    user_id INTEGER REFERENCES users(id)  
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_videos_title ON videos(title);
CREATE INDEX IF NOT EXISTS idx_videos_user_id ON videos(user_id);

-- Note: Admin user should be created through the registration endpoint
-- This ensures proper password hashing
-- Use: POST /register with {"username":"admin","password":"admin"}