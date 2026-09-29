"""Create or reset a login account (lockout recovery).

    python3 set_admin_password.py <email> <password> [name]

Run it on the server (PythonAnywhere -> Bash) from the project folder, e.g.

    python3 set_admin_password.py dev@mindwatch.local 'YourNewStrongPw123'

It creates the account if it does not exist yet, otherwise it just replaces
the password. Use a strong password - this account opens the feedback inbox.

The script loads .env exactly like the web app does, so it always writes to
the same database file the site actually reads from.
"""

import os
import sqlite3
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from werkzeug.security import check_password_hash, generate_password_hash

from database import _db_path


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1

    email = argv[1].strip().lower()
    password = argv[2]
    name = argv[3] if len(argv) > 3 else "Developer"

    if len(password) < 8:
        print("Password must be at least 8 characters.")
        return 1

    db_path = _db_path()
    print(f"Database : {db_path}")
    print(f"Exists   : {os.path.exists(db_path)}")
    print(f"Size     : {os.path.getsize(db_path) if os.path.exists(db_path) else 0} bytes")
    print(f"MINDWATCH_DB_FILE = {os.environ.get('MINDWATCH_DB_FILE') or '(not set)'}")
    print(f"MINDWATCH_ADMIN_EMAIL = {os.environ.get('MINDWATCH_ADMIN_EMAIL') or '(not set)'}")
    print("-" * 60)

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    hashed = generate_password_hash(password)

    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        cursor.execute(
            "UPDATE users SET password = ? WHERE email = ?",
            (hashed, email),
        )
        action = "updated"
    else:
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, hashed),
        )
        action = "created"

    connection.commit()

    # Read back and prove the new password really verifies.
    cursor.execute(
        "SELECT password FROM users WHERE email = ?", (email,)
    )
    row = cursor.fetchone()
    verified = bool(row and check_password_hash(row[0], password))

    cursor.execute("SELECT email FROM users ORDER BY id")
    accounts = [r[0] for r in cursor.fetchall()]

    cursor.close()
    connection.close()

    print(f"Account {action}: {email}")
    print(f"Password verifies: {verified}")
    print(f"Accounts in this database: {accounts}")
    print("-" * 60)
    if not verified:
        print("FAILED - password was not stored correctly.")
        return 1
    print("Now click Web -> Reload, then log in with this email and password.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
