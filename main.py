# main.py
import eventlet
eventlet.monkey_patch()  # MUST be first

import os
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
# typing set: set of client_id currently typing
typing_set = set()

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("join")
def handle_join(data):
    """
    data: { client_id: <string> }
    """
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
    """
    data: { client_id: <string>, text: <string> }
    """
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
    # broadcast the message to all
    socketio.emit("new_message", message)

@socketio.on("typing")
def handle_typing(data):
    """
    data: { client_id: <string>, typing: bool }
    We'll update typing_set and broadcast an aggregate status that indicates whether ANY other user is typing.
    """
    client_id = data.get("client_id")
    is_typing = bool(data.get("typing", False))

    if not client_id:
        return

    if is_typing:
        typing_set.add(client_id)
    else:
        typing_set.discard(client_id)

    # Broadcast typing info: server will send which client_ids are typing (small set)
    socketio.emit("typing_update", {"typing_clients": list(typing_set)})

@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    client_id = connected.pop(sid, None)
    if client_id and client_id in typing_set:
        typing_set.discard(client_id)
    broadcast_online_count()
    # update typing_set broadcast
    socketio.emit("typing_update", {"typing_clients": list(typing_set)})

def broadcast_online_count():
    # number of unique connected client_ids
    unique_clients = set(connected.values())
    online_count = len(unique_clients)
    socketio.emit("online_count", {"online": online_count})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
