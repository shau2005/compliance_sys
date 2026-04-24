import os
import psycopg
from psycopg.rows import dict_row
import dotenv

dotenv.load_dotenv()

def get_connection() -> psycopg.Connection:
    """
    Returns a configured psycopg database connection using dict_row factory.
    """
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "tenant_db")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")

    try:
        conn = psycopg.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            row_factory=dict_row
        )
        return conn
    except Exception as e:
        raise ConnectionError(f"Database connection failed: {e}")
