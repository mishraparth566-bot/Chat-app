import eventlet
eventlet.monkey_patch()  # MUST be first

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from tinydb import TinyDB, Query
from datetime import datetime
import uuid
import os

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = "change-this-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# TinyDB path in project root
DB_PATH = os.path.join(os.path.dirname(__file__), "chat_db.json")
db = TinyDB(DB_PATH)
messages_table = db.table("messages")

online_count = 0

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("connect")
def on_connect():
    global online_count
    online_count += 1
    # send full history only to connecting client (oldest -> newest)
    emit("chat_history", messages_table.all())
    # broadcast presence (everyone sees online count)
    emit("presence", {"online": online_count}, broadcast=True)

@socketio.on("disconnect")
def on_disconnect():
    global online_count
    online_count = max(0, online_count - 1)
    emit("presence", {"online": online_count}, broadcast=True)

@socketio.on("send_message")
def on_send_message(data):
    """
    Client sends:
      { client_id, text, time? }
    Behavior:
      - server generates server_id
      - persist message: { id, text, time, status }
      - emit status_update to sender (client_id -> server_id, status=delivered)
      - broadcast receive_message to all other clients (include_self=False)
    """
    client_id = data.get("client_id")
    text = (data.get("text") or "").strip()
    if not text:
        return

    # Prefer client-provided time for 'accurate' client local timestamp; fallback to server time
    timestamp = data.get("time") or datetime.now().strftime("%H:%M")
    server_id = str(uuid.uuid4())

    doc = {
        "id": server_id,
        "text": text,
        "time": timestamp,
        "status": "sent"
    }

    # persist
    messages_table.insert(doc)

    # tell the sender their temp message was persisted and deliver mapping
    emit("status_update", {
        "client_id": client_id,
        "server_id": server_id,
        "status": "delivered"
    })

    # broadcast to other clients
    emit("receive_message", doc, broadcast=True, include_self=False)

@socketio.on("message_read")
def on_message_read(data):
    """
    Called by clients when they have displayed/read a message.
    Expects { id: server_id }
    Updates DB status to 'read' and broadcasts update
    """
    server_id = data.get("id")
    if not server_id:
        return

    Message = Query()
    messages_table.update({"status": "read"}, Message.id == server_id)
    emit("status_update", {"server_id": server_id, "status": "read"}, broadcast=True)

if __name__ == "__main__":
    # use PORT env var if provided
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
