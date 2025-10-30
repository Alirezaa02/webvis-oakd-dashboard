import time
from db import init_schema, db

if __name__ == "__main__":
    init_schema()
    now = int(time.time() * 1000)
    with db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT IGNORE INTO ops_log (ts, level, message) VALUES (%s,%s,%s)",
            (now, "INFO", "flask:init_db complete")
        )
    print("DB ready.")
