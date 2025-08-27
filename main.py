import eventlet
eventlet.monkey_patch()   # must be first

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from tinydb import TinyDB
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# setup TinyDB database
db = TinyDB("chat_db.json")

@app.route("/")
def index():
    # load all past messages from DB
    messages = db.all()
    return render_template("index.html", messages=messages)

@socketio.on("send_message")
def handle_message(data):
    message = {
        "user": data["user"],
        "msg": data["msg"],
        "timestamp": datetime.now().strftime("%H:%M"),
        "status": "sent"  # default stage
    }

    # save in DB
    db.insert(message)

    # broadcast to all users
    emit("receive_message", message, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000)
