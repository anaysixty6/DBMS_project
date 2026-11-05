# Run this once if you want to use the sample admin account.
# It changes admin@collabcampus.com password to a secure hash of admin123.
from werkzeug.security import generate_password_hash
from database import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
hashed = generate_password_hash("admin123")
cur.execute(
    "UPDATE users SET password_hash=%s WHERE email=%s AND role='admin'",
    (hashed, "admin@collabcampus.com")
)
print("Admin password updated. Login: admin@collabcampus.com / admin123")
cur.close()
conn.close()
