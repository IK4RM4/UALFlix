import psycopg2
import os

def get_db_connection():
    DB_HOST = os.environ.get('DB_HOST', 'ualflix_db')  # Corrigido para 'ualflix_db'
    DB_NAME = os.environ.get('DB_NAME', 'ualflix')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'password')
    
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

def check_db_connection():
    try:
        conn = get_db_connection()
        conn.close()
        return True
    except:
        return False