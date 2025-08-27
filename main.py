import eventlet
eventlet.monkey_patch()  # MUST be first

from flask import Flask, render_template
from flask_socketio import SocketIO, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# Initialize SocketIO with eventlet
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('message')
def handleMessage(msg):
    """
    msg is expected as a dict: {user: username, text: message}
    """
    print(f"{msg['user']}: {msg['text']}")
    send(msg, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
