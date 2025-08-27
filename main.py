from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from tinydb import TinyDB

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Persistent storage
db = TinyDB('chat.json')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/messages')
def get_messages():
    return {'messages': db.all()}

@socketio.on('send_message')
def handle_send_message(msg):
    db.insert(msg)  # Save persistently
    emit('message_received', msg, broadcast=True, include_self=False)
    emit('update_status', {'msg_id': msg['id'], 'status':'received'}, to=request.sid)

@socketio.on('message_read')
def handle_message_read(msg):
    emit('update_status', {'msg_id': msg['id'], 'status':'read'}, broadcast=True, include_self=False)

if __name__ == '__main__':
    socketio.run(app, debug=True)
