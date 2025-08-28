# main.py
import eventlet
eventlet.monkey_patch()  # MUST be first

import os
import time
from threading import Lock
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from tinydb import TinyDB
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

DB_PATH = "chat_db.json"
db = TinyDB(DB_PATH)
messages_table = db.table("messages")

# mapping: sid -> client_id
connected = {}
# typing state
typing_set = set()
typing_last_seen = {}  # client_id -> last typing timestamp
typing_lock = Lock()

TYPING_TIMEOUT = 1.2  # matches client-side timeout


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("join")
def handle_join(data):
    client_id = data.get("client_id")
    sid = request.sid
    connected[sid] = client_id
    # send existing messages to this client
    all_messages = messages_table.all()
    emit("load_messages", all_messages)
    # broadcast online count
    broadcast_online_count()


@socketio.on("send_message")
def handle_send_message(data):
    client_id = data.get("client_id")
    text = data.get("text", "").strip()
    if not text:
        return

    message = {
        "id": datetime.utcnow().isoformat() + "_" + (client_id or "anon"),
        "client_id": client_id,
        "text": text,
        "time": datetime.utcnow().isoformat()
    }
    messages_table.insert(message)
    socketio.emit("new_message", message)


@socketio.on("typing")
def handle_typing(data):
    client_id = data.get("client_id")
    is_typing = bool(data.get("typing", False))
    if not client_id:
        return

    with typing_lock:
        if is_typing:
            typing_set.add(client_id)
            typing_last_seen[client_id] = time.time()
        else:
            typing_set.discard(client_id)
            typing_last_seen.pop(client_id, None)

    # broadcast only to others (not self)
    socketio.emit(
        "typing_update",
        {"typing_clients": list(typing_set)},
        broadcast=True,
        include_self=False
    )


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    client_id = connected.pop(sid, None)
    if client_id:
        with typing_lock:
            typing_set.discard(client_id)
            typing_last_seen.pop(client_id, None)
    broadcast_online_count()
    socketio.emit("typing_update", {"typing_clients": list(typing_set)}, broadcast=True)


def broadcast_online_count():
    unique_clients = set(connected.values())
    online_count = len(unique_clients)
    socketio.emit("online_count", {"online": online_count})


# background task: cleanup stale typing states
def typing_cleaner():
    while True:
        now = time.time()
        expired = []
        with typing_lock:
            for cid, ts in list(typing_last_seen.items()):
                if now - ts > TYPING_TIMEOUT:
                    expired.append(cid)
            for cid in expired:
                typing_set.discard(cid)
                typing_last_seen.pop(cid, None)
        if expired:
            socketio.emit("typing_update", {"typing_clients": list(typing_set)}, broadcast=True)
        eventlet.sleep(1)  # check every 1s


# launch cleaner
eventlet.spawn(typing_cleaner)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
