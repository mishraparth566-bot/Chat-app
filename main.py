import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from datetime import datetime
from tinydb import TinyDB
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode="eventlet")

# Setup TinyDB
db = TinyDB("db.json")
messages_table = db.table("messages")

@app.route('/')
def index():
    messages = messages_table.all()  # load saved messages
    return render_template('index.html', messages=messages)

@socketio.on('send_message')
def handle_send_message(data):
    timestamp = datetime.now().strftime("%H:%M")  # accurate time
    message = {
        "text": data['text'],
        "sender": data['sender'],
        "timestamp": timestamp,
        "status": "sent"
    }

    # Save to DB
    messages_table.insert(message)

    # Broadcast message
    emit('receive_message', message, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
