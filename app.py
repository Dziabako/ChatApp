# Flask webserver runs socketserver will run different clients that connects to the flask webserver
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
# Generate random room codes
import random
# Generate random room codes
from string import ascii_uppercase

app = Flask(__name__)
app.config["SECRET_KEY"] = "sjdfhkjahskdjfh"
socketio = SocketIO(app)


# Storing data about created rooms / checking if the room exists and avoiding generating same code
rooms = {}


def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        # Checking if code exist as a key in rooms / if code is not in rooms break the loop
        if code not in rooms:
            break

    return code


@app.route('/', methods=['GET', 'POST'])
def index():
    # Clearing session to allow user to change room or join again
    session.clear()

    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        # False will be returned if join or create is None / without it would be just None
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            # Last to variables are for avoinding reentering same data from the user after failed attempt
            return render_template('index.html', error="Name is required", code=code, name=name)
        
        if join is not False and not code:
            return render_template('index.html', error="Code is required to join a room", code=code, name=name)
        
        # Checking which room user is trying to enter
        # If the room exists user will join otherwise room code will be generated
        room = code

        if create is not False:
            room = generate_unique_code(4)
            # Data stored for each generated room
            rooms[room] = {
                "members": 0,
                "messages": []
            }
        elif code not in rooms:
            return render_template('index.html', error="Room does not exist", code=code, name=name)
        
        # Temporary storing session data without advanced authentication / after refreshing user dont need to reenter the data
        session["room"] = room
        session["name"] = name

        return redirect(url_for("room"))


    return render_template('index.html')


@app.route('/room')
def room():
    # Preventing to go to /room without registration
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("index"))

    # Last variable keep chat hiostory when one user refreshes the page
    return render_template("room.html", code=room, messages = rooms[room]["messages"])


# Sending message to serves which then sends it futher / Here should be stored when the message was sent
@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }

    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said {data['data']}")



# Connecting to socketio rooms
@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")

    # Making sure that there is a name and room existing
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    # Joining room
    join_room(room)
    send({
        "name": name,
        "message": f"{name} has joined the room"
    }, to=room)
    rooms[room]["members"] += 1
    print(f"{name} has joined the room {room}")
    

# Leaving the room
@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")

    leave_room(room)

    # Check if the user which left was in the rooms / If there is no users in room delete room
    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]

    send({
        "name": name,
        "message": f"{name} has left the room"
    }, to=room)
    print(f"{name} has left the room {room}")


if __name__ == '__main__':
    socketio.run(app, debug=True)
