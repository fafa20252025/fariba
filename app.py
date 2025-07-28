from flask import Flask, request, render_template, redirect, url_for, session
from flask_socketio import join_room, leave_room, emit, SocketIO
import random
from string import ascii_letters, digits

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=True)

rooms = {}  # Stores room data globally


def generate_unique_code(length=4):
    while True:
        code = ''.join(random.choices(ascii_letters + digits, k=length)).upper()
        if code not in rooms:
            return code


@app.route('/', methods=['GET', 'POST'])
def home():
    session.clear()
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code', '').upper()
        join = 'join' in request.form
        create = 'create' in request.form

        if not name:
            return render_template('home.html', error="Please enter your name.", code=code, name=name)

        if create:
            room = generate_unique_code()
            rooms[room] = {"members": [], "messages": []}
        elif join:
            if not code:
                return render_template('home.html', error="Please enter a room code to join.", code=code, name=name)
            room = code
            if room not in rooms:
                return render_template('home.html', error="Room code does not exist.", code=code, name=name)
        else:
            return render_template('home.html', error="Invalid action.", code=code, name=name)

        session['room'] = room
        session['name'] = name
        return redirect(url_for("room"))

    return render_template('home.html')


@app.route('/room')
def room():
    room = session.get('room')
    name = session.get('name')

    if room is None or name is None or room not in rooms:
        session.clear()
        return redirect(url_for('home'))

    return render_template('room.html', code=room, name=name, members=rooms[room]["members"], messages=rooms[room]["messages"])


@app.route('/leave', methods=['POST'])
def leave():
    room = session.get('room')
    name = session.get('name')

    if room in rooms and name in rooms[room]["members"]:
        rooms[room]["members"].remove(name)
        socketio.emit('message', {'name': 'System', 'message': f'{name} has left the room.'}, to=room)

    session.clear()
    return redirect(url_for('home'))


@socketio.on('send_message')
def handle_message(data):
    room = session.get('room')
    name = session.get('name')

    print("🔔 'send_message' triggered:", data)

    if not room or not name or room not in rooms:
        print("⚠️ Invalid session or room.")
        return

    message = data.get('data', '').strip()
    if message == '':
        return

    print(f"💬 Message from {name} in room {room}: {message}")
    emit('message', {'name': name, 'message': message}, to=room)
    rooms[room]["messages"].append({'name': name, 'message': message})


@socketio.on("connect")
def connect():
    room = session.get('room')
    name = session.get('name')

    if not room or not name or room not in rooms:
        return False

    join_room(room)
    emit('message', {'name': 'System', 'message': f'{name} has entered the room.'}, to=room)
    if name not in rooms[room]["members"]:
        rooms[room]["members"].append(name)
    print(f"✅ {name} has joined room {room}. Members: {rooms[room]['members']}")


@socketio.on("disconnect")
def disconnect():
    room = session.get('room')
    name = session.get('name')

    if room and name:
        leave_room(room)
        if room in rooms and name in rooms[room]["members"]:
            rooms[room]["members"].remove(name)
            emit('message', {'name': 'System', 'message': f'{name} has left the room.'}, to=room)
            print(f"❌ {name} has left room {room}. Remaining: {rooms[room]['members']}")


if __name__ == '__main__':
    socketio.run(app, debug=True)
