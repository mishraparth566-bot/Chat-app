import eventlet
eventlet.monkey_patch()  # keep FIRST

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from tinydb import TinyDB, Query
from datetime import datetime
import uuid

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

db = TinyDB("chat.json")
messages = db.table("messages")

online = 0

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("connect")
def on_connect():
    global online
    online += 1
    # send full history to ONLY the joining client
    emit("chat_history", messages.all())
    # broadcast presence
    emit("presence", {"online": online}, broadcast=True)

@socketio.on("disconnect")
def on_disconnect():
    global online
    online = max(0, online - 1)
    emit("presence", {"online": online}, broadcast=True)

@socketio.on("send_message")
def on_send(data):
    """
    data = { client_id, text, time }
    """
    client_id = data.get("client_id")
    text = (data.get("text") or "").strip()
    if not text:
        return
    # use client local time if provided, else server time
    timestamp = data.get("time") or datetime.now().strftime("%H:%M")
    server_id = str(uuid.uuid4())

    doc = {
        "id": server_id,
        "text": text,
        "time": timestamp,
        "status": "sent"
    }
    messages.insert(doc)

    # tell the sender their temp message is delivered + real id
    emit("status_update", {
        "client_id": client_id,
        "server_id": server_id,
        "status": "delivered"
    })

    # broadcast the new message to everyone ELSE (avoid duplicate for sender)
    emit("receive_message", doc, broadcast=True, include_self=False)

@socketio.on("message_read")
def on_read(data):
    """Mark a message as read and broadcast."""
    server_id = data.get("id")
    if not server_id:
        return
    Message = Query()
    messages.update({"status": "read"}, Message.id == server_id)
    emit("status_update", {"server_id": server_id, "status": "read"}, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000)
