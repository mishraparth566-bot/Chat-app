import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
from tinydb import TinyDB
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')

# Database
db = TinyDB('chat.json')
messages_table = db.table('messages')

online_users = set()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    username = request.sid
    online_users.add(username)
    emit('status', {'msg': 'A user is online'}, broadcast=True)

    # Send chat history to newly connected user
    history = messages_table.all()
    emit('chat_history', history)

@socketio.on('disconnect')
def handle_disconnect():
    username = request.sid
    if username in online_users:
        online_users.remove(username)
    emit('status', {'msg': 'A user went offline'}, broadcast=True)

@socketio.on('send_message')
def handle_message(data):
    msg_text = data['msg']
    username = data.get('username', 'User')

    timestamp = datetime.now().strftime("%H:%M")

    message = {
        'username': username,
        'msg': msg_text,
        'timestamp': timestamp,
        'status': 'sent'
    }

    # Save in DB
    messages_table.insert(message)

    # Broadcast to all clients
    emit('receive_message', message, broadcast=True)

@socketio.on('update_status')
def update_status(data):
    # Update read receipts (dummy simulation)
    msg_id = data.get('id')
    status = data.get('status')
    # In real DB you’d update specific message, TinyDB can too if needed
    emit('status_update', {'id': msg_id, 'status': status}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
