This program is meant to simulate an auction house.


To run the game locally (for now) run:
python3 GameServer.py "port" "UserInfo.txt"

UserInfo.txt can be any text file but I have included this one to be the pair of usernames and passwords that will be needed later. Usernames and passwords can be added to the text file. 
An example would be 
python3 GameServer.py 12345 UserInfo.txt


Once the server is running, more terminal can be opened and used as "players". 
To run a player do:
python3 GameClient.py "ip" "port"

The port is the same port as the one used in the server and the ip should be a local ip for now. So
An example would be
python3 GameClient.py 127.0.0.1 12345. 


Once a player is in the server they are asked to authenticate themselves using the username and password on the file. If they are not on the file they won't be let in. 
Once a player has entered the game they are in the hall. In the hall, players have three options:

/exit - exits the enter game
/list - lists the count of rooms, their amount of players, and the status of the room
/enter room_number - enters the room with associated room number. 

Players may only enter rooms that have the "available" status and not the "playing status". 


Once a player is in the room they can ready up by using the "/ready" command. Once a room has more than two players and everyone is ready the bidding game starts. 
The game is played like this:

  Each player has 30 points that they can split between 6 slots. 
  To bid an amount of points in each slot they do /bids _ _ _ _ _ _ where each of the subsequent 6 numbers is a bid for that associated slot. 
  These slots are then compared to each player and the player with the highest bid on that slot wins one point(ties will give points to both players). 
  At the end of the game, the player with the most points wins!
  Bids of negative or over 30 points will result in an automatic loss. 

Upon completion of the game, players are returned to the hall and can join another room or exit the game. 
