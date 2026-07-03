import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta

# Database file location relative to backend root
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BACKEND_DIR, "data", "auth.db")

def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes database tables for users and sessions."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

# Password Hashing Utilities using pbkdf2_hmac (zero extra binary dependencies)
def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Hashes a password with PBKDF2 HMAC SHA-256 and returns (hash_hex, salt_hex)."""
    if salt is None:
        salt = secrets.token_hex(16)
        
    salt_bytes = bytes.fromhex(salt)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        100000 # 100k iterations is standard and fast enough for dashboards
    )
    return pw_hash.hex(), salt

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verifies that the password matches the stored hash."""
    pw_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(pw_hash, password_hash)

# User Management operations
def create_user(username: str, password: str) -> bool:
    """Creates a new user record in the database. Returns True if successful, False otherwise."""
    if not username or not password:
        return False
    username = username.strip().lower()
        
    password_hash, salt = hash_password(password)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, password_hash, salt)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Username already exists
        return False
    finally:
        conn.close()

def get_user(username: str) -> dict | None:
    """Retrieves a user by username."""
    if not username:
        return None
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

# Session Token operations
def create_session(username: str, days_expiry: int = 7) -> str:
    """Creates a new session token for the user, stores it in SQLite, and returns the token."""
    username = username.strip().lower()
    token = secrets.token_hex(32)
    expires_at = datetime.now() + timedelta(days=days_expiry)
    expires_at_str = expires_at.isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessions (token, username, expires_at) VALUES (?, ?, ?)",
        (token, username, expires_at_str)
    )
    conn.commit()
    conn.close()
    return token

def get_session(token: str) -> dict | None:
    """Retrieves a session from the database if active and not expired."""
    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM sessions WHERE token = ?", (token,)).fetchone()
    
    if not row:
        conn.close()
        return None
        
    session = dict(row)
    expires_at = datetime.fromisoformat(session["expires_at"])
    
    if expires_at < datetime.now():
        # Session expired, delete it
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None
        
    conn.close()
    return session

def delete_session(token: str) -> bool:
    """Deletes a session (logout)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
    changes = conn.total_changes
    conn.commit()
    conn.close()
    return changes > 0

# Auto-initialize database on import
init_db()
