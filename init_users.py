import getpass
from werkzeug.security import generate_password_hash
from db import get_db_connection

accounts = [
    ("author01", "author"),
    ("editor01", "editor")
]

conn = get_db_connection()

try:
    with conn.cursor() as cur:
        for username, role in accounts:
            password = getpass.getpass(f"請輸入 {username} 的密碼：")

            password_hash = generate_password_hash(password)

            cur.execute("""
                INSERT INTO users (username, password, role)
                VALUES (%s, %s, %s)
                ON CONFLICT (username) DO NOTHING
            """, (username, password_hash, role))

    conn.commit()
    print("帳號建立完成！")

finally:
    conn.close()