import os
import pymysql
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv(override=True)

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "webvis")
DB_PASS = os.getenv("DB_PASS", "webvis_pw")
DB_NAME = os.getenv("DB_NAME", "webvis")

def get_conn():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASS,
        database=DB_NAME, autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
        charset="utf8mb4"
    )

@contextmanager
def db() :
    conn = get_conn()
    try:
        yield conn
    finally:
        try: conn.close()
        except: pass

def init_schema():
    schema_sql = """
    CREATE TABLE IF NOT EXISTS users (
      id INT PRIMARY KEY AUTO_INCREMENT,
      username VARCHAR(32) UNIQUE NOT NULL,
      pass_hash CHAR(60) NOT NULL,
      role ENUM('admin','user') NOT NULL DEFAULT 'user'
    );

    CREATE TABLE IF NOT EXISTS sensor_readings (
      ts BIGINT PRIMARY KEY,
      temp FLOAT,
      pressure FLOAT,
      humidity FLOAT,
      light FLOAT,
      gas FLOAT
    );

    CREATE TABLE IF NOT EXISTS detections (
      id BIGINT PRIMARY KEY AUTO_INCREMENT,
      ts BIGINT NOT NULL,
      frame_id VARCHAR(64) NOT NULL,
      image_url MEDIUMTEXT NOT NULL,
      aruco_id INT,
      valve_state ENUM('open','closed'),
      conf FLOAT,
      bbox JSON,
      INDEX (ts)
    );

    CREATE TABLE IF NOT EXISTS poses (
      ts BIGINT PRIMARY KEY,
      x FLOAT NOT NULL,
      y FLOAT NOT NULL,
      z FLOAT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS ops_log (
      ts BIGINT PRIMARY KEY,
      level ENUM('INFO','WARN','ERROR') NOT NULL,
      message TEXT NOT NULL
    );
    """
    with db() as conn:
        cur = conn.cursor()
        for stmt in schema_sql.split(";\n"):
            s = stmt.strip()
            if s:
                cur.execute(s)
