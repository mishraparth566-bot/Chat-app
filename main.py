import eventlet
eventlet.monkey_patch()   # MUST be the very first thing

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
from tinydb import TinyDB, Query
from datetime import datetime
import uuid

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# TinyDB store
db = TinyDB("chat_db.json")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/messages")
def get_messages():
    # return all stored messages as JSON
    return jsonify(db.all())

@socketio.on("send_message")
def handle_send_message(data):
    """
    Expected data from client:
    { client_id: <string>, user: <string>, text: <string>, time: <string> }
    """
    client_id = data.get("client_id")
    user = data.get("user", "Anonymous")
    text = data.get("text", "")
    time = data.get("time") or datetime.now().strftime("%H:%M")

    # create server id
    server_id = str(uuid.uuid4())

    # build canonical message
    message = {
        "id": server_id,
        "client_id": client_id,
        "user": user,
        "text": text,
        "time": time,
        "status": "sent"  # initial status
    }

    # persist message
    db.insert(message)

    # broadcast the message to all OTHER clients (not the sender)
    socketio.emit("receive_message", message, broadcast=True, include_self=False)

    # notify the sender that message was accepted & mapped -> delivered (server side)
    # include client_id so the sender can match its temp message element
    socketio.emit("status_update", {
        "client_id": client_id,
        "server_id": server_id,
        "status": "delivered"
    }, to=request.sid)

@socketio.on("message_read")
def handle_message_read(data):
    """
    data: { id: <server_id> }
    When a client reads (renders) a message, update DB and notify everyone.
    """
    server_id = data.get("id")
    if not server_id:
        return

    Message = Query()
    db.update({"status": "read"}, Message.id == server_id)

    # broadcast read status to all (so sender sees blue ticks)
    socketio.emit("status_update", {"server_id": server_id, "status": "read"}, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000, debug=True)
