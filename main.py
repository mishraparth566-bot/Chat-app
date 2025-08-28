from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import time, uuid, eventlet
from threading import Lock

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

connected = {}            # sid -> client_id
typing_set = set()        # who is typing
typing_last_seen = {}     # client_id -> last typing timestamp
typing_lock = Lock()

TYPING_TIMEOUT = 1.2  # seconds (matches frontend timeout)


@app.route("/")
def index():
    return render_template("index.html")


# ----------------- Typing Indicator -----------------
@socketio.on("typing")
def handle_typing(data):
    client_id = data.get("client_id")
    is_typing = bool(data.get("typing", False))
    if not client_id:
        return

    with typing_lock:
        if is_typing:
            typing_set.add(client_id)
            typing_last_seen[client_id] = time.time()
        else:
            typing_set.discard(client_id)
            typing_last_seen.pop(client_id, None)

    socketio.emit(
        "typing_update",
        {"typing_clients": list(typing_set)},
        broadcast=True,
        include_self=False,
    )


def typing_cleaner():
    while True:
        now = time.time()
        expired = []
        with typing_lock:
            for cid, ts in list(typing_last_seen.items()):
                if now - ts > TYPING_TIMEOUT:
                    expired.append(cid)
            for cid in expired:
                typing_set.discard(cid)
                typing_last_seen.pop(cid, None)
        if expired:
            socketio.emit("typing_update", {"typing_clients": list(typing_set)}, broadcast=True)
        eventlet.sleep(1)


eventlet.spawn(typing_cleaner)


# ----------------- Messaging + Receipts -----------------
@socketio.on("send_message")
def handle_message(data):
    client_id = data.get("client_id")
    text = data.get("text")
    if not client_id or not text:
        return

    msg_id = str(uuid.uuid4())
    timestamp = int(time.time())

    socketio.emit("new_message", {
        "id": msg_id,
        "client_id": client_id,
        "text": text,
        "timestamp": timestamp,
    }, broadcast=True)


@socketio.on("message_read")
def handle_read(data):
    message_id = data.get("message_id")
    if not message_id:
        return
    socketio.emit("message_read_update", {
        "message_id": message_id
    }, broadcast=True)


# ----------------- Disconnect Handling -----------------
@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    client_id = connected.pop(sid, None)
    if client_id:
        with typing_lock:
            typing_set.discard(client_id)
            typing_last_seen.pop(client_id, None)
    socketio.emit("typing_update", {"typing_clients": list(typing_set)}, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, debug=True)
