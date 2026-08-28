import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    source TEXT, account TEXT, date TEXT,
    counterparty TEXT, description TEXT, category TEXT,
    amount REAL, bucket TEXT, flag TEXT, review TEXT, raw_json TEXT
);
CREATE TABLE IF NOT EXISTS balances (
    account TEXT PRIMARY KEY, name TEXT, balance REAL, as_of TEXT
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

TXN_COLS = ["id","source","account","date","counterparty","description",
            "category","amount","bucket","flag","review","raw_json"]

def init_db(conn):
    conn.executescript(SCHEMA)
    conn.commit()

def upsert_transaction(conn, row):
    placeholders = ",".join("?" for _ in TXN_COLS)
    updates = ",".join(f"{c}=excluded.{c}" for c in TXN_COLS if c != "id")
    conn.execute(
        f"INSERT INTO transactions ({','.join(TXN_COLS)}) VALUES ({placeholders}) "
        f"ON CONFLICT(id) DO UPDATE SET {updates}",
        [row.get(c) for c in TXN_COLS])
    conn.commit()

def upsert_balance(conn, account, name, balance, as_of):
    conn.execute(
        "INSERT INTO balances (account,name,balance,as_of) VALUES (?,?,?,?) "
        "ON CONFLICT(account) DO UPDATE SET name=excluded.name, "
        "balance=excluded.balance, as_of=excluded.as_of",
        [account, name, balance, as_of])
    conn.commit()

def set_meta(conn, key, value):
    conn.execute("INSERT INTO meta (key,value) VALUES (?,?) "
                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value", [key, value])
    conn.commit()

def get_meta(conn, key):
    r = conn.execute("SELECT value FROM meta WHERE key=?", [key]).fetchone()
    return r[0] if r else None


def add_question(conn, text):
    conn.execute("INSERT INTO questions (text) VALUES (?)", [text])
    conn.commit()


def list_questions(conn):
    return conn.execute(
        "SELECT id, text, created_at FROM questions ORDER BY id DESC").fetchall()


def delete_question(conn, qid):
    conn.execute("DELETE FROM questions WHERE id=?", [qid])
    conn.commit()
