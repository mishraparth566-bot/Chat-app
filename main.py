from flask import Flask, render_template
from flask_socketio import SocketIO, send

# create flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# home route
@app.route('/')
def index():
    return render_template('index.html')

# handle chat messages
@socketio.on('message')
def handleMessage(msg):
    print('Message: ' + msg)   # log message on server
    send(msg, broadcast=True)  # send to all connected users

# run app
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
