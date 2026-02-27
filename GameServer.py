#!/usr/bin/python3

import random
import sys
import socket
import threading
from collections import Counter

class ServerThread(threading.Thread):
    def __init__(self, client, users, roomMembers, roomState, mutex):
        threading.Thread.__init__(self)

        self.client = client
        #a dictionary of users and the correlated username/password combos
        self.users = users
        #a dictionary of room members that will be used to store rooms and the members in the room
        self.roomMembers = roomMembers
        #alternates between available and playing for joinability of palyers
        self.roomState = roomState
        #lock needed when messing with the global variables above
        self.mutex = mutex


        self.username = None
        #alternates from authenticating, in the halls, in a room, and playing
        self.state = "auth"
        self.currentRoom = None
        #room status for players
        self.ready = False
        #/bid needs 6 values after it always for the bid game
        self.bids = None
        self.connectionSocket = None
        #if player is invalid (i.e. if they bid a negative number or go over 30)
        self.invalid = False
        self.submitted = False

    #the run function has all the necessary states that should redirect to various helper functions
    #these states are correlated to the self.state variable above
    def run(self):
        connectionSocket, addr = self.client
        self.connectionSocket = connectionSocket
        try:
            while True:
                #authentication state
                if self.state == "auth":
                    sentence = connectionSocket.recv(1024)
                    if not sentence:
                        return None
                    guess = sentence.decode().strip()
                    parts = guess.split()

                    #parses the username and password from the input
                    if len(parts) == 2:
                        username, password = parts[0], parts[1]
                        #checks the username against the user database
                        if username in self.users and self.users[username] == password:
                            self.username = username
                            self.state = "hall"
                            connectionSocket.sendall("1001 Authentication successful\n".encode())
                        else:
                            connectionSocket.sendall("1002 Authentication failed\n".encode())
                    else:
                        connectionSocket.sendall("4002 Unrecognized message\n".encode())

                #in hall state
                elif self.state == "hall":
                    sentence = connectionSocket.recv(1024)
                    if not sentence:
                        return None
                    guess = sentence.decode().strip()
                    parts = guess.split()

                    #three commands possible for the players here: /list, /exit, and /enter
                    #list does not affect state and just returns a list of rooms gotten from the room information
                    #exit exits the program and sends a message
                    #enter comes with a room number and can change states depending on if room is available or playing
                    if len(parts) == 1 and parts[0] == "/list":
                        self.listCommand(connectionSocket)

                    elif len(parts) == 1 and parts[0] == "/exit":
                        connectionSocket.sendall("4001 Bye bye\n".encode())
                        return

                    elif len(parts) == 2 and parts[0] == "/enter":
                        self.playerEnterRoom(connectionSocket, parts[1])

                    else:
                        connectionSocket.sendall("4002 Unrecognized message\n".encode())

                #player is now in a room and can exist in two partial states
                #"room" represents being in a "waiting room" where player can be both ready and not ready but not playing
                #"playing" represents being in the room and playing the game
                elif self.state in ("room", "playing"):
                    sentence = connectionSocket.recv(1024)
                    if not sentence:
                        self.playerDisconnects()
                        return None
                    guess = sentence.decode().strip()
                    parts = guess.split()

                    #as the winner dictates where the state goes, the losers are often left stuck at this state
                    #this segment checks the state again and determines the correct state it needs to be in and runs
                    if self.state == "hall":
                        if len(parts) == 1 and parts[0] == "/list":
                            self.listCommand(connectionSocket)
                        elif len(parts) == 1 and parts[0] == "/exit":
                            connectionSocket.sendall("4001 Bye bye\n".encode())
                            return
                        elif len(parts) == 2 and parts[0] == "/enter":
                            self.playerEnterRoom(connectionSocket, parts[1])
                        else:
                            connectionSocket.sendall("4002 Unrecognized message\n".encode())
                        continue


                    if self.state == "room":
                        if len(parts) == 1 and parts[0] == "/ready":
                            self.playerReady(connectionSocket)
                        else:
                            connectionSocket.sendall("4002 Unrecognized message\n".encode())
                    else:
                        if len(parts) == 7 and parts[0] == "/bids":
                            self.bidHandler(connectionSocket, parts[1:])
                        else:
                            connectionSocket.sendall("4002 Unrecognized message\n".encode())


        finally:
            connectionSocket.close()

    #handles the ready state meaning when the player calls "/ready" this helper is called
    #helper also determines if the room is full leading to all players changing state and game commencement
    def playerReady(self, connectionSocket):
        room = self.currentRoom

        with self.mutex:
            self.ready = True
            connectionSocket.sendall("3012 Ready\n".encode())

            members = self.roomMembers[room]

            #check if already playing and members are greater than or equal to 2 and everyone is ready.
            if (
                    self.roomState[room] != "playing"
                    and len(members) >= 2
                    and all(m.ready for m in members)
            ):
                self.roomState[room] = "playing"

                for m in members:
                    m.state = "playing"
                    m.connectionSocket.sendall("3013 Game starts. Please submit your bids\n".encode())

    #playerDisconnects handles the case in which a player disconnects from a room.
    #disconnects can result in commencement of the game, declaration of a winner, or removal of a bid
    def playerDisconnects(self):
        with self.mutex:
            room = self.currentRoom
            temp = self.state

            self.roomMembers[room].remove(self)
            members = list(self.roomMembers[room])

            #if someone is disconnected from the game and leaves one, that person automatically becomes winner
            if temp == "playing":
                if len(members) == 1:
                    members[0].connectionSocket.sendall("3021 You are the winner\n".encode())
                    self.roomState[room] = "available"
                    for m in list(self.roomMembers[room]):
                        m.state = "hall"
                        m.currentRoom = None
                        m.ready = False
                        m.submitted = False
                        m.invalid = False
                        m.bids = None
                    self.roomMembers[room].clear()
                else:
                    #checking if the remaining players are ready
                    if members and all(m.submitted for m in members):
                        winners, losers = self.winlose(members)
                        for w in winners:
                            w.connectionSocket.sendall("3021 You are the winner\n".encode())
                        for l in losers:
                            l.connectionSocket.sendall("3022 You lost this game\n".encode())
                        self.roomState[room] = "available"
                        for m in list(self.roomMembers[room]):
                            m.state = "hall"
                            m.currentRoom = None
                            m.ready = False
                            m.submitted = False
                            m.invalid = False
                            m.bids = None
                        self.roomMembers[room].clear()

    #creates a list of rooms using their member count and status and shows it to the client requesting it
    def listCommand(self, connection):
        with self.mutex:
            #take roomMember count and roomState from global data and append them to this array
            res = []
            for i in range (1, len(self.roomMembers) + 1):
                res.append(f"{len(self.roomMembers[i])}:{self.roomState[i]}")
            msg = f"3001 {len(self.roomMembers)} " + " ".join(res) + "\n"

        connection.sendall(msg.encode())

    #handles the command of a player trying to enter a room. rejects the player if the room is playing
    def playerEnterRoom(self, connectionSocket, room_num):
        #check if room_num is numeric/is an int
        try:
            room = int(room_num)
        except ValueError:
            connectionSocket.sendall("4002 Unrecognized message\n".encode())
            return

        #check if the given room number from enter command is within the range of rooms determined by game
        if room not in self.roomMembers:
            connectionSocket.sendall("4002 Unrecognized message\n".encode())
            return

        with self.mutex:
            if self.roomState[room] == "playing":
                connectionSocket.sendall("3014 The room is playing a game\n".encode())
                return

            self.currentRoom = room
            self.ready = False
            self.submitted = False
            self.invalid = False
            self.bids = None
            self.state = "room"

            self.roomMembers[room].append(self)

        connectionSocket.sendall("3011 In room, not ready\n".encode())

    def bidHandler(self, connectionSocket, bidValues):
        room = self.currentRoom
        try:
            bids = [int(x) for x in bidValues]
        except ValueError:
            bids = []

        valid = len(bids) == 6 and all(b >= 0 for b in bids)and sum(bids) <= 30

        with self.mutex:
            self.submitted = True
            if valid:
                self.invalid = False
                self.bids = bids
            else:
                self.invalid = True
                self.bids = [0,0,0,0,0,0]

            members = list(self.roomMembers[room])

            if len(members) == 1:
                winner = members[0]
                winner.connectionSocket.sendall("3021 You are the winner\n".encode())
                self.roomState[room] = "available"
                for m in list(self.roomMembers[room]):
                    m.state = "hall"
                    m.currentRoom = None
                    m.ready = False
                    m.submitted = False
                    m.invalid = False
                    m.bids = None
                self.roomMembers[room].clear()
                return

            if not all(m.submitted for m in members):
                return

            winners, losers = self.winlose(members)

            for w in winners:
                w.connectionSocket.sendall("3021 You are the winner\n".encode())
            for l in losers:
                l.connectionSocket.sendall("3022 You lost this game\n".encode())

            self.roomState[room] = "available"
            for m in list(self.roomMembers[room]):
                m.state = "hall"
                m.currentRoom = None
                m.ready = False
                m.submitted = False
                m.invalid = False
                m.bids = None
            self.roomMembers[room].clear()

    def winlose(self, members):
        valid_players = [m for m in members if not m.invalid]
        invalid_players = [m for m in members if m.invalid]

        if not valid_players:
            return ([], members)
        winCounts = {m: 0 for m in valid_players}

        for i in range(6):
            max_bid = max(m.bids[i] for m in valid_players)
            for m in valid_players:
                if m.bids[i] == max_bid:
                    winCounts[m] += 1

        best = max(winCounts.values())
        winners = [m for m in valid_players if winCounts[m] == best]
        losers = [m for m in members if m not in winners]  # includes invalids automatically

        return (winners, losers)

class ServerMain:
    def __init__(self, port, userFile):
        self.port = port
        self.users = self.parseUserFile(userFile)

        self.room_count = 5
        self.roomMembers = {i: [] for i in range(1, self.room_count + 1)}
        self.roomState = {i: "available" for i in range(1, self.room_count + 1)}

        self.mutex = threading.Lock()

    def parseUserFile(self, userFile):
        users = {}

        with open(userFile, "r") as f:
            for line in f:
                line = line.strip()

                if ":" not in line:
                    continue

                username, password = line.split(":", 1)
                username = username.strip()
                password = password.strip()
                users[username] = password

        return users

    def server_run(self):
        serverPort = self.port
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSocket.bind(('', serverPort))
        serverSocket.listen(5)

        while True:
            client = serverSocket.accept()
            t = ServerThread(client, self.users, self.roomMembers, self.roomState, self.mutex)
            t.start()

if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(1)

    port = int(sys.argv[1])
    userFile = sys.argv[2]

    server = ServerMain(port, userFile)
    server.server_run()