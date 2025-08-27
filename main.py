from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('send_message')
def handle_send_message(msg):
    # Broadcast to all other clients (received)
    emit('message_received', msg, broadcast=True, include_self=False)
    # Notify sender that message is received
    emit('update_status', {'msg_id': msg['id'], 'status':'received'}, to=request.sid)

@socketio.on('message_read')
def handle_message_read(msg):
    # Broadcast read status to sender
    emit('update_status', {'msg_id': msg['id'], 'status':'read'}, broadcast=True, include_self=False)

if __name__ == '__main__':
    socketio.run(app, debug=True)
