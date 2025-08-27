from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from tinydb import TinyDB

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

db = TinyDB('chat.json')
clients = {}  # key: sid, value: username

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/messages')
def get_messages():
    return {'messages': db.all()}

@socketio.on('connect')
def handle_connect():
    clients[request.sid] = "User"
    emit('update_online', list(clients.values()), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in clients:
        del clients[request.sid]
        emit('update_online', list(clients.values()), broadcast=True)

@socketio.on('set_name')
def handle_set_name(name):
    clients[request.sid] = name
    emit('update_online', list(clients.values()), broadcast=True)

@socketio.on('send_message')
def handle_send_message(msg):
    db.insert(msg)
    emit('message_received', msg, broadcast=True, include_self=False)
    emit('update_status', {'msg_id': msg['id'], 'status':'received'}, to=request.sid)

@socketio.on('message_read')
def handle_message_read(msg):
    emit('update_status', {'msg_id': msg['id'], 'status':'read'}, broadcast=True, include_self=False)

@socketio.on('typing')
def handle_typing(data):
    emit('show_typing', data, broadcast=True, include_self=False)

if __name__ == '__main__':
    socketio.run(app, debug=True)
