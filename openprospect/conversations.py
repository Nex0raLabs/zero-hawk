"""Unified conversation storage and read APIs."""
from .db import connect, log


def ensure_schema():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS conversations(
          id INTEGER PRIMARY KEY AUTOINCREMENT, channel TEXT NOT NULL,
          external_id TEXT NOT NULL UNIQUE, contact_address TEXT DEFAULT '',
          subject TEXT DEFAULT '', last_message TEXT DEFAULT '', unread INTEGER DEFAULT 0,
          status TEXT DEFAULT 'open', notes TEXT DEFAULT '',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS conversation_messages(
          id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER NOT NULL,
          direction TEXT NOT NULL, body TEXT NOT NULL, external_id TEXT DEFAULT '',
          status TEXT DEFAULT 'received', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_conversation_message_external
          ON conversation_messages(external_id) WHERE external_id<>'' ;
        """)
        columns = {row["name"] for row in c.execute("PRAGMA table_info(conversations)")}
        if "notes" not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN notes TEXT DEFAULT ''")
        message_columns = {row["name"] for row in c.execute("PRAGMA table_info(conversation_messages)")}
        if "status" not in message_columns:
            c.execute("ALTER TABLE conversation_messages ADD COLUMN status TEXT DEFAULT 'received'")


def list_conversations(limit=200):
    ensure_schema()
    with connect() as c:
        return [dict(x) for x in c.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC,id DESC LIMIT ?", (limit,)
        )]


def get_conversation(conversation_id):
    ensure_schema()
    with connect() as c:
        row = c.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()
        return dict(row) if row else None


def list_messages(conversation_id, limit=300):
    ensure_schema()
    with connect() as c:
        return [dict(x) for x in c.execute(
            "SELECT * FROM conversation_messages WHERE conversation_id=? ORDER BY id ASC LIMIT ?",
            (conversation_id, max(1, min(int(limit), 500))),
        )]


def mark_read(conversation_id):
    ensure_schema()
    with connect() as c:
        c.execute("UPDATE conversations SET unread=0 WHERE id=?", (conversation_id,))


def update_conversation(conversation_id, *, status=None, notes=None):
    ensure_schema()
    with connect() as c:
        if status is not None:
            if status not in {"open", "needs_you", "closed"}:
                raise ValueError("Invalid conversation status.")
            c.execute("UPDATE conversations SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                      (status, conversation_id))
        if notes is not None:
            c.execute("UPDATE conversations SET notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                      (str(notes)[:4000], conversation_id))


def update_message_status(external_id, status):
    ensure_schema()
    if status not in {"sent", "delivered", "read", "failed", "received"}:
        return
    with connect() as c:
        c.execute("UPDATE conversation_messages SET status=? WHERE external_id=?", (status, external_id))


def add_message(channel, external_id, address, subject, body, direction="inbound"):
    """Append an idempotent message to a conversation grouped by channel and address."""
    ensure_schema()
    conversation_key = channel + ":" + (address or external_id).strip().lower()
    with connect() as c:
        c.execute(
            "INSERT OR IGNORE INTO conversations(channel,external_id,contact_address,subject,last_message,unread) VALUES(?,?,?,?,?,?)",
            (channel, conversation_key, address, subject, body[:12000], 1 if direction == "inbound" else 0),
        )
        row = c.execute("SELECT id FROM conversations WHERE external_id=?", (conversation_key,)).fetchone()
        if row:
            cur = c.execute(
                "INSERT OR IGNORE INTO conversation_messages(conversation_id,direction,body,external_id,status) VALUES(?,?,?,?,?)",
                (row["id"], direction, body[:12000], external_id, "received" if direction == "inbound" else "sent"),
            )
            if cur.rowcount:
                c.execute(
                    "UPDATE conversations SET last_message=?,updated_at=CURRENT_TIMESTAMP,"
                    "unread=CASE WHEN ?='inbound' THEN 1 ELSE unread END WHERE id=?",
                    (body[:12000], direction, row["id"]),
                )
    log("conversation_message", f"{channel} {direction} {address}")
