import eventlet
eventlet.monkey_patch()

import time, uuid, sqlite3
from flask import Flask, render_template, request
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

DB_FILE = "chat.db"

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    client_id TEXT,
                    text TEXT,
                    timestamp INTEGER,
                    status TEXT
                )""")
    conn.commit()
    conn.close()

init_db()

def save_message(mid, cid, text, ts, status="sent"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?)", (mid, cid, text, ts, status))
    conn.commit()
    conn.close()

def get_messages():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM messages ORDER BY timestamp ASC")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "client_id": r[1], "text": r[2], "timestamp": r[3], "status": r[4]} for r in rows]

# --- Online users ---
online_users = set()

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("connect")
def connect():
    online_users.add(request.sid)
    socketio.emit("chat_history", get_messages(), to=request.sid)
    if len(online_users) > 1:
        socketio.emit("online_status", {"status": "Online"}, broadcast=True)

@socketio.on("disconnect")
def disconnect():
    online_users.discard(request.sid)
    if len(online_users) <= 1:
        socketio.emit("online_status", {"status": ""}, broadcast=True)

# --- Messaging ---
@socketio.on("send_message")
def handle_send(data):
    cid, text = data.get("client_id"), data.get("text")
    if not text: return
    mid, ts = str(uuid.uuid4()), int(time.time())
    save_message(mid, cid, text, ts)
    socketio.emit("new_message", {
        "id": mid, "client_id": cid, "text": text,
        "timestamp": ts, "status": "sent"
    }, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, debug=True)
