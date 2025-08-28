import eventlet
eventlet.monkey_patch()   # ✅ must come first before any other imports

import time
import uuid
import sqlite3
from flask import Flask, render_template, request
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

DB_FILE = "chat.db"


# ----------------- Database -----------------
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


def save_message(msg_id, client_id, text, timestamp, status="sent"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?)", (msg_id, client_id, text, timestamp, status))
    conn.commit()
    conn.close()


def update_status(msg_id, status):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE messages SET status=? WHERE id=?", (status, msg_id))
    conn.commit()
    conn.close()


def get_messages():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM messages ORDER BY timestamp ASC")
    rows = c.fetchall()
    conn.close()
    return [
        {"id": r[0], "client_id": r[1], "text": r[2], "timestamp": r[3], "status": r[4]}
        for r in rows
    ]


init_db()


# ----------------- Online Tracking -----------------
online_users = set()


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():
    online_users.add(request.sid)
    if len(online_users) > 1:
        socketio.emit("online_status", {"status": "Online"}, broadcast=True)
    socketio.emit("chat_history", get_messages(), to=request.sid)


@socketio.on("disconnect")
def handle_disconnect():
    online_users.discard(request.sid)
    if len(online_users) <= 1:
        socketio.emit("online_status", {"status": ""}, broadcast=True)


# ----------------- Messaging -----------------
@socketio.on("send_message")
def handle_message(data):
    client_id = data.get("client_id")
    text = data.get("text")
    if not text:
        return

    msg_id = str(uuid.uuid4())
    timestamp = int(time.time())

    save_message(msg_id, client_id, text, timestamp, status="sent")

    socketio.emit("new_message", {
        "id": msg_id,
        "client_id": client_id,
        "text": text,
        "timestamp": timestamp,
        "status": "sent"
    }, broadcast=True)


@socketio.on("message_received")
def handle_received(data):
    msg_id = data.get("message_id")
    update_status(msg_id, "received")
    socketio.emit("message_status", {"message_id": msg_id, "status": "received"}, broadcast=True)


@socketio.on("message_read")
def handle_read(data):
    msg_id = data.get("message_id")
    update_status(msg_id, "read")
    socketio.emit("message_status", {"message_id": msg_id, "status": "read"}, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, debug=True)
