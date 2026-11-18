import psycopg
from config import DB_CONFIG

def get_db_connection():
    conn = psycopg.connect(**DB_CONFIG)
    return conn