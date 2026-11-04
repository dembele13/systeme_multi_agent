import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "livraison"),
        user=os.getenv("DB_USER", "livraison"),
        password=os.getenv("DB_PASSWORD", "2003"),
        cursor_factory=RealDictCursor,
    )