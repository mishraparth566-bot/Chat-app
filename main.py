# main.py
import eventlet
eventlet.monkey_patch()  # must be first

import os
import time
from threading import Lock
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from tinydb import TinyDB
from datetime import datetime
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
app = Flask(__name__)
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

DB_PATH = "chat_db.json"
db = TinyDB(DB_PATH)
messages_table = db.table("messages")

# connections
connected = {}  # sid -> client_id
typing_set = set()
typing_last_seen = {}
typing_lock = Lock()
TYPING_TIMEOUT = 1.2


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("join")
def handle_join(data):
    client_id = data.get("client_id")
    sid = request.sid
    connected[sid] = client_id

    # send all messages to client
    all_messages = messages_table.all()
    emit("load_messages", all_messages)

    # broadcast online count
    broadcast_online_count()

    # mark all messages as delivered for this client
    mark_delivered(client_id)


def mark_delivered(client_id):
    updated = []
    for msg in messages_table.all():
        if msg["client_id"] != client_id and msg.get("status") == "sent":
            msg["status"] = "delivered"
            messages_table.update({"status": "delivered"}, doc_ids=[msg.doc_id])
            updated.append(msg)
    if updated:
        socketio.emit("update_messages", updated)


@socketio.on("send_message")
def handle_send_message(data):
    client_id = data.get("client_id")
    text = data.get("text", "").strip()
    if not text:
        return
now_ist = datetime.now(IST)

message = {
    "id": now_ist.isoformat() + "_" + (client_id or "anon"),
    "client_id": client_id,
    "text": text,
    "time": now_ist.isoformat()  # save full IST timestamp
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

    socketio.emit(
        "typing_update",
        {"typing_clients": list(typing_set)},
        broadcast=True,
        include_self=False
    )


@socketio.on("mark_read")
def handle_mark_read(data):
    client_id = data.get("client_id")
    updated = []
    for msg in messages_table.all():
        if msg["client_id"] != client_id and msg.get("status") != "read":
            msg["status"] = "read"
            messages_table.update({"status": "read"}, doc_ids=[msg.doc_id])
            updated.append(msg)
    if updated:
        socketio.emit("update_messages", updated)


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
    online_count = len(set(connected.values()))
    socketio.emit("online_count", {"online": online_count})


# background cleanup
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
        eventlet.sleep(1)


eventlet.spawn(typing_cleaner)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
