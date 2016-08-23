#Mybook

> Prototype of a privacy focused P2P social network.

This web app Requires:  

- CherryPy 3.1.2 or 7.1.0 (www.cherrypy.org)
- Python (use 2.7)                         
- Jinja2   (http://jinja.pocoo.org)

This social network consists of multiple peers and a centralized address
server to check up other peers' addresses.

You can set up multiple peers in a network by making copies of this folder and 
change the listen_port in MybookServer.py and run them all on the same machine. 
The default ip and port is set as 127.0.0.1:8080 make sure you change the port
for each peer.

If you want to test on multiple machines each represents a peer then make sure
you change the ip accordingly or set it to 0.0.0.0 for public ip and turn on
finding own ip through ip.42.pl. Also make sure you change the address server's
code where the valid ip range includes all peers' ip range. 

Run the address server first in the addrServer folder. The address server
has default address of 127.0.0.1:10001. The central server has to be running
for peer to check others' ip addresses. Run python MybookServer.py to start 
up the peer server. Register an account and start posting text messages, 
events, photos.

In this network friendship is done by two one way friendships. A one way
friendship is achieved by peer A requests peer B for friendship through
visiting peer B's profile by the "Who Is Online?" on right hand side panel.
Peer A would be asked to choose a key to use for accesing peer B's site in
future. Right after the request, peer A should go edit friend on peer A's own
site to add peer B and store the key which peer A just chose for accessing
peer B's site. Vice versa peer B has to do the same thing to achieve another one way
friendship. Only a friendship with two successful one way friendships is
considered as a real friendship

Data transfers are only successful if both friends are logged in online. All
data are transferred in standard formats as encoded json messages.Session is used for identification to secure peer's data. clientKey is the key
for accessing client and hostKey is the key for accessing host

Since this is a prototype many features have not been polished and completed
to full extend. Gallery is not completed yet, it only shows user's photos on
the top side and friends' below.
