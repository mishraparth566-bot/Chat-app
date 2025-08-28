from flask import Flask, render_template, request, jsonify
from tinydb import TinyDB
from datetime import datetime

app = Flask(__name__)
db = TinyDB("chat_db.json")
messages_table = db.table("messages")

# simple global typing status
typing_status = {"typing": False}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/messages", methods=["GET"])
def get_messages():
    return jsonify(messages_table.all())

@app.route("/messages", methods=["POST"])
def add_message():
    data = request.get_json()
    user = data.get("user")
    text = data.get("text")

    if not user or not text:
        return jsonify({"error": "User and text required"}), 400

    new_message = {
        "user": user,
        "text": text,
        "time": datetime.utcnow().isoformat()
    }
    messages_table.insert(new_message)
    return jsonify(new_message), 201

# typing indicator routes
@app.route("/typing", methods=["POST"])
def set_typing():
    data = request.get_json()
    typing_status["typing"] = bool(data.get("typing"))
    return jsonify({"status": "ok"})

@app.route("/typing", methods=["GET"])
def get_typing():
    return jsonify(typing_status)

if __name__ == "__main__":
    app.run(debug=True)
