import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from tinydb import TinyDB

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

db = TinyDB("chat_db.json")
messages_table = db.table("messages")

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("send_message")
def handle_send_message(data):
    messages_table.insert({"user": data["user"], "text": data["text"]})
    emit("receive_message", data, broadcast=True)

@socketio.on("typing")
def handle_typing(data):
    emit("typing", data, broadcast=True, include_self=False)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
