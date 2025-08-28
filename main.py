# MUST be first to avoid the monkey patch error
import eventlet
eventlet.monkey_patch()

import time
import uuid
import sqlite3
from flask import Flask, render_template, request
from flask_socketio import SocketIO

app = Flask(__name__)
# Use eventlet async mode (monkey_patched above)
socketio = SocketIO(app, cors_allowed_origins="*")

DB_FILE = "chat.db"

# ----------------- Database -----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            text TEXT,
            timestamp INTEGER,
            status TEXT
        )"""
    )
    conn.commit()
    conn.close()

def save_message(msg):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (id, client_id, text, timestamp, status) VALUES (?, ?, ?, ?, ?)",
        (msg["id"], msg["client_id"], msg["text"], msg["timestamp"], msg["status"]),
    )
    conn.commit()
    conn.close()

def update_status(message_id, status):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE messages SET status=? WHERE id=?", (status, message_id))
    conn.commit()
    conn.close()

def fetch_all_messages():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, client_id, text, timestamp, status FROM messages ORDER BY timestamp ASC")
    rows = c.fetchall()
    conn.close()
    return [
        {"id": r[0], "client_id": r[1], "text": r[2], "timestamp": r[3], "status": r[4]}
        for r in rows
    ]

init_db()

# ----------------- Online presence -----------------
# Track socket sid -> client_id for unique online count
connected = {}  # sid -> client_id

def broadcast_online():
    # number of unique client_ids
    online = len(set(connected.values()))
    socketio.emit("online_count", {"online": online}, broadcast=True)

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("connect")
def on_connect():
    # client will immediately send 'join' with its persisted client_id
    pass

@socketio.on("join")
def on_join(data):
    client_id = data.get("client_id") or "anon"
    connected[request.sid] = client_id
    # Send full history to just this client
    socketio.emit("chat_history", fetch_all_messages(), to=request.sid)
    broadcast_online()

@socketio.on("disconnect")
def on_disconnect():
    connected.pop(request.sid, None)
    broadcast_online()

# ----------------- Messaging & Receipts -----------------
@socketio.on("send_message")
def on_send_message(data):
    client_id = data.get("client_id")
    text = (data.get("text") or "").strip()
    if not text:
        return
    msg = {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "text": text,
        "timestamp": int(time.time()),
        "status": "sent",  # initial status for sender
    }
    save_message(msg)
    # Broadcast to everyone (sender also receives it to render uniformly)
    socketio.emit("new_message", msg, broadcast=True)

@socketio.on("message_received")
def on_message_received(data):
    # A recipient has received the message (delivered)
    message_id = data.get("message_id")
    if not message_id:
        return
    update_status(message_id, "received")
    socketio.emit("message_status", {"message_id": message_id, "status": "received"}, broadcast=True)

@socketio.on("message_read")
def on_message_read(data):
    # A recipient has read the message
    message_id = data.get("message_id")
    if not message_id:
        return
    update_status(message_id, "read")
    socketio.emit("message_status", {"message_id": message_id, "status": "read"}, broadcast=True)

if __name__ == "__main__":
    # eventlet WSGI is used implicitly by Flask-SocketIO when eventlet is installed
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
