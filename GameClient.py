#!/usr/bin/python3
import sys
import socket
import select

if len(sys.argv) != 3:
    print("Wrong amount of arguments")
    sys.exit(1)

host = sys.argv[1]
port = int(sys.argv[2])

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientSocket.connect((host, port))

while True:
    username = input("Please input your user name:\n")
    password = input("Please input your password:\n")

    login_msg = f"{username} {password}\n"
    clientSocket.sendall(login_msg.encode())

    response = clientSocket.recv(1024)
    if not response:
        print("Login disconnected")
        sys.exit(0)

    response = response.decode().strip()
    print(response)

    if response.startswith("1001"):
        break


#unfortunately I could not find out a way for the multiple socket stuff to find things and had to ask the internet
#i.e. gemini told me to use select.
#I have implemented select through trying to look through libraries.
while True:


    readable, _, _ = select.select([clientSocket, sys.stdin], [], [])

    for r in readable:

        #server saying something
        if r is clientSocket:
            data = clientSocket.recv(1024)
            if not data:
                print("Disconnected from server.")
                sys.exit(0)

            print(data.decode().strip())

        #user typing
        elif r is sys.stdin:
            cmd = sys.stdin.readline()
            if not cmd:
                continue

            clientSocket.sendall(cmd.encode())