import sqlite3
import hashlib

# Database helper functions
def init_db():
    with sqlite3.connect('user_data.db') as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'User'
            )
        ''')
        conn.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    password_hash = hash_password(password)
    with sqlite3.connect('user_data.db') as conn:
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, "User")',
                      (username, password_hash))
            conn.commit()
        except sqlite3.IntegrityError:
            return "User already exists."

def check_login(username, password):
    password_hash = hash_password(password)
    with sqlite3.connect('user_data.db') as conn:
        c = conn.cursor()
        c.execute('SELECT role FROM users WHERE username = ? AND password_hash = ?',
                  (username, password_hash))
        result = c.fetchone()
        if result:
            return result[0]  # Return the user's role
        else:
            return None  # Login failed

def update_user_role(username, new_role):
    with sqlite3.connect('user_data.db') as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username))
        conn.commit()

# Initialize the database when this file is executed
init_db()
