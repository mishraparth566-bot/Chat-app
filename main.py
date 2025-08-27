import eventlet
eventlet.monkey_patch()  # this must be the first line

from flask import Flask, render_template
from flask_socketio import SocketIO
from tinydb import TinyDB
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# TinyDB database
db = TinyDB("chat_db.json")

@app.route("/")
def index():
    messages = db.all()
    return render_template("index.html", messages=messages)

@socketio.on("send_message")
def handle_message(data):
    message = {
        "user": data.get("user", "Anonymous"),
        "msg": data["msg"],
        "timestamp": datetime.now().strftime("%H:%M"),
        "status": "sent"
    }

    # Save to DB
    db.insert(message)

    # Broadcast to all clients
    socketio.emit("receive_message", message, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000, debug=True)
