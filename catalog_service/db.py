import psycopg2
import psycopg2.extras


def get_db_connection():
    conn = psycopg2.connect(
        host="0.0.0.0",
        database="ualflix",
        user="postgres",
        password="password",
        port=5432,
    )

    return conn
