import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from tinydb import TinyDB, Query
from datetime import datetime
import uuid

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

db = TinyDB("chat_db.json")

@app.route("/")
def index():
    messages = db.all()
    return render_template("index.html", messages=messages)

@socketio.on("send_message")
def handle_send(data):
    msg_id = str(uuid.uuid4())
    message = {
        "id": msg_id,
        "user": data.get("user", "Anonymous"),
        "msg": data["msg"],
        "timestamp": datetime.now().strftime("%H:%M"),
        "status": "sent"
    }
    db.insert(message)
    emit("receive_message", message, broadcast=True)

@socketio.on("update_status")
def handle_status(data):
    """Update message read/delivered status"""
    Message = Query()
    db.update({"status": data["status"]}, Message.id == data["id"])
    emit("status_update", data, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000, debug=True)
