"""Create or reset a login account (lockout recovery).

    python3 set_admin_password.py <email> <password> [name]

Run it on the server (PythonAnywhere -> Bash) from the project folder, e.g.

    python3 set_admin_password.py dev@mindwatch.local 'YourNewStrongPw123'

It creates the account if it does not exist yet, otherwise it just replaces
the password. Use a strong password - this account opens the feedback inbox.
"""

import sqlite3
import sys

from werkzeug.security import generate_password_hash

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

    connection = sqlite3.connect(_db_path())
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
    cursor.close()
    connection.close()

    print(f"Account {action}: {email}")
    print("You can now log in at /login with that email and password.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
