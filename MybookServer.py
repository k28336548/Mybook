#!/usr/bin/python
"""
    @file MybookServer.py
    @author: D. Chen 2012
             Built upon the hello world template and CherryPy configuration written by C. Coghill 2012
    @date Apr 2012
    @brief  This prototype uses the CherryPy web server (from www.cherrypy.org)
            to host a simple web application for a small private social network.
"""
"""
    The central server has to be running for peer to check others' ip addresses

    In this network friendship is done by two one way friendships.
    A one way friendship is achieved by peer A requests peer B for friendship 
    by visiting peer B's profile through the "who is online" on right hand side panel.
    Peer A would be asked to choose a key to use for accesing peer B's site in future.
    Right after the request, peer A should edit friend on his/her own site to add peer B 
    and store the key he/she chose for accessing peer B's site.

    Vice versa peer B has to do the same thing to achieve another one way friendship.
    Only a friendship with two successful one way friendships is considered as a real friendship

    Data transactions are only successful if both friends are logged in online.
    Session is used for identification to secure peer's data.
    clientKey is the key for accessing client and hostKey is the key for accessing host

    Since this is a prototype many features have not been polished and completed to full extend.
    Gallery is not completed yet, it only shows user's photos on the top side and friends' below 
"""

# Requires:  CherryPy 3.1.2 or 7.1.0 (www.cherrypy.org)
#            Python  (use 2.7)
#            Jinja2   jinja.pocoo.org

import cherrypy
import os
import logging as log
import urllib
import urllib2
import json
import sqlite3
import time
import cookielib

# The address we listen for connections on
listen_ip = "127.0.0.1" # set this to 0.0.0.0 for public IP
listen_port = 8080 # set to different port if testing multiple running on the same machine
server_addr = "127.0.0.1:10001" # central server for checking other peers' addresses

# Folders for images, html templates and css stylesheet
staticfolder = "static"
template_folder = "templates"
css_folder = "css"


# Tell Jinja we want to load templates from a folder called "templates"
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader(template_folder))

# Data base setting
db = sqlite3.connect("db/main.db")
curs = db.cursor()

# Manually set my ip for testing purpose else use public ip in real scenario
ip = listen_ip

# Set my ip to public ip through ip.42.pl
#ip = urllib2.urlopen('http://ip.42.pl/raw').read()

myAddr = str(ip)+":"+str(listen_port)

cookies = cookielib.CookieJar()
urlopener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))

#User information
userID = None
friendList = []
signedIn = False

def findOnlineInfo():
    """ Connect to the address server and it returns a list of online people's info
       e.g. ["127.0.0.1,8080,a123,1471418551.07", ...]
    """
    URL = "http://%s" % (server_addr, )
    method = "whoonline"
    onlineList = []
    try:
        fptr = urlopener.open("%s/%s" % (URL, method))
        onlineList = fptr.readlines()
        fptr.close()
    except: # central server down
        pass

    return onlineList

def findOnlineIDs(userID):
    """ Return a list of all the online users' ids """
    onlinelist = findOnlineInfo()
    onlineIDs =[]
    for index in range(len(onlinelist)):
        person = onlinelist[index].split(",")
        # id index in online info is 2
        if person[2] != userID:
            onlineIDs.append(person[2])

    return onlineIDs

def findOnlineFriends(friendList):
    """ Return a list of friends' ids who are currently online """
    onlineFriends = []
    onlineIDs = findOnlineIDs(userID)   
    for friend in friendList:
        for id_ in onlineIDs:
            if friend == id_:
                onlineFriends.append(friend)

    return onlineFriends

def findUserInfo(username):
    """ Return specific user's info 
        format: [username, password, name, sex, mail, aboutme, day, month, year]
    """
    userInfo = []
    db = sqlite3.connect('db/main.db')
    curs = db.cursor()
    data = curs.execute('''SELECT * FROM user WHERE username=?''', [username])
    if not data:
        pass
    else:
        for elements in data:
            for element in elements:
                userInfo.append(element)

    return userInfo

def findAllUsers():
    """ Return a list of users' ids on this machine(host) """
    users = []
    db = sqlite3.connect('db/main.db')
    curs = db.cursor()
    usernames = curs.execute('''SELECT username FROM user''')
    for username in usernames:
        users.append(username[0])

    return users

def findIP(clientID):
    """ Return the IP of a specific client who is currently online """
    onlineList = findOnlineInfo()
    for index in range(len(onlineList)):
        person = onlineList[index].split(",")
        if person[2] == clientID:
            clientIP = person[0]
            break
    
    return clientIP

def findPort(clientID):
    """ Return the port of a specific client who is currently online"""
    onlineList = findOnlineInfo()
    for index in range(len(onlineList)):
        person = onlineList[index].split(",")
        if person[2] == clientID:
            clientPort = person[1]
            break

    return clientPort

def simpleOnlineList(onlineList, userID):
    """Simplify the list of online info to return only [[ip, port, id],...]
       Only include other people who are currently online not the host
    """
    onlineSimpList =[] #need to change this
    for index in range(len(onlineList)):
        person = onlineList[index].split(",")
        # index 2 is username in online info
        if person[2] != userID:
            onlineSimpList.append([person[0], person[1], person[2]])

    return onlineSimpList

def getTexts():
    """ Return a list of host's friends' and host's text messages that are stored in host db """
    db = sqlite3.connect('db/main.db')
    curs = db.cursor()
    data = curs.execute('''SELECT creator, created, link, body FROM message WHERE creator=? OR creator IN (SELECT clientID FROM friend WHERE hostID=? and friend=1) ORDER BY id DESC''', [userID, userID])
    statusUpdates = []
    for message in data:
        statusUpdates.append(message)

    return statusUpdates

def getEvents():
    """ Return a list of host's friends' and host's events that are stored in host db """
    db = sqlite3.connect('db/main.db')
    curs = db.cursor()
    data = curs.execute('''SELECT creator, created, link, body, day, month, year FROM event WHERE creator=? OR creator IN (SELECT clientID FROM friend WHERE hostID=? and friend=1) ORDER BY id DESC''', [userID, userID])
    events = []
    for event in data:
        events.append(event)

    return events

def getPhotos():
    """ Return a list of host's photos that are stored in host db """
    db = sqlite3.connect('db/main.db')
    curs = db.cursor()
    data = curs.execute('''SELECT name FROM photo WHERE creator=? ORDER BY id DESC''', [userID])
    photos = []
    for photo in data:
        photos.append(photo[0])

    return photos

def getUserPassword(username):
    """ Get the password of a specific user """
    db = sqlite3.connect('db/main.db')
    cursor = db.cursor()
    password = cursor.execute('''SELECT password FROM user WHERE username=?''', [username])
    password = [element for element in password]
        
    if not password:
        userPassword = None
    else:
        userPassword = password[0][0]

    return userPassword

def loadFriendList(username):
    """ Load friends of current user to the global friend list """
    global friendList
    friendList = []
    db = sqlite3.connect("db/main.db")
    curs = db.cursor()
    data = curs.execute('''SELECT clientID FROM friend WHERE hostID=? AND friend=1''', [username])
    for friend in data:
        friendList.append(friend[0])

def setuserID(username):
    """ Set current user's id as global user id """
    global userID
    userID = username


def stdPhoto(photoID):
    """ Take a photo message, specified by photo id, from db and turn it
        into a standard photo message across the network 
        photo format in db: [id, creator, created, link, body, name]
    """
    stdPhoto = {'creator':None, 'created':None, 'link':None, 'type':2, 'body':None}
    db = sqlite3.connect("db/main.db")
    curs = db.cursor()
    data = curs.execute('''SELECT * FROM photo WHERE id=? ORDER BY id''', [photoID])
    for element in data:
        stdPhoto['creator'] = element[1]
        stdPhoto['created'] = time.mktime(time.strptime(element[2])) # convert to epoch time
        stdPhoto['link'] = element[3]
        stdPhoto['body'] = element[4]
    return stdPhoto

def stdEvent(eventID):
    """ Take a event, specified by event id, from db and turn it
        into a standard event message across the network 
        event format in db: [id, creator, created, link, body, day, month, year]
    """
    stdEvent = {'creator':None, 'created':None, 'link':None, 'type':3, 'body':None, 'year':None, 'month':None, 'day':None }
    db = sqlite3.connect("db/main.db")
    curs = db.cursor()
    data = curs.execute('''SELECT * FROM event WHERE id=? ORDER BY id''', [eventID])
    for element in data:
        stdEvent['creator'] = element[1]
        stdEvent['created'] = time.mktime(time.strptime(element[2]))
        stdEvent['link'] = element[3]
        stdEvent['body'] = element[4]
        stdEvent['day'] = element[5]
        stdEvent['month'] = element[6]
        stdEvent['year'] = element[7]

    return stdEvent

def stdMessage(messageID):
    """ Take a text message, specified by message id, from db and turn it 
        into a standard text message across the network 
        message format in db: [id, creator, created, link, body, body]
    """
    stdMessage = {'creator':None, 'created':None, 'link':None, 'type':1, 'body':None}
    db = sqlite3.connect("db/main.db")
    curs = db.cursor()
    data = curs.execute('''SELECT * FROM message WHERE id=? ORDER BY id''', [messageID])
    for element in data:
        date = time.mktime(time.strptime(element[2]))
        stdMessage['creator'] = element[1]
        stdMessage['created'] = time.mktime(time.strptime(element[2]))
        stdMessage['link'] = element[3]
        stdMessage['body'] = element[4]

    return stdMessage

def storeMessage(message):
    """ Store a new message from current user's post """
    db = sqlite3.connect('db/main.db')
    cursor = db.cursor()
    now = time.ctime()
    cursor.execute('''INSERT INTO message (creator, created, body) VALUES (?,?,?)''', (userID, now, message))
    db.commit()

    # Insert link as well
    data = cursor.execute('''SELECT id FROM message WHERE body=? AND created=?''', [message, now])
    for element in data:
        id_ = element[0]
    link = "/updates?id=%s" % id_
    cursor.execute('''UPDATE message SET link=? WHERE body=? AND created=?''', [link, message, now])
    db.commit()

def storeEvent(day, month, year, description):
    """ Store a new event that current user has created """
    db = sqlite3.connect("db/main.db")
    curs = db.cursor()
    now = time.ctime()
    curs.execute('''INSERT INTO event (creator, created, day, month, year, body) VALUES (?,?,?,?,?,?)''', (userID, now, day, month, year, description))
    db.commit()

    # Insert link as well
    data = curs.execute('''SELECT id FROM event WHERE body=? AND created=?''', [description, now])
    for number in data:
        randomId = number[0]
    link = "/seeevent?id=%s" % randomId
    curs.execute('''UPDATE event SET link=? WHERE body=? AND created=?''', [link, description, now])
    db.commit()

def storePhoto(newPhoto, body):
    """ Store a new photo that current user has uploaded """
    now = time.ctime()
    rawfname = newPhoto.filename
    fname = os.path.split(rawfname)[1]
    data = newPhoto.file.read()
    f = open(staticfolder + "/img/" + fname, 'wb') # this has to be 'wb' for it to work on Windows else image corrupts
    f.write(data)
    f.close()

    db = sqlite3.connect('db/main.db')
    curs = db.cursor()
    curs.execute('''INSERT INTO photo (creator, created, body, name, link) VALUES (?,?,?,?,"/seephoto?id=")''', (userID, now, body, fname))
    db.commit()

    # Insert link as well
    data = curs.execute('''SELECT id FROM photo WHERE link="/seephoto?id="''')
    for number in data:
        randomId = number[0]
    link = "/seephoto?id=%s" % randomId
    curs.execute('''UPDATE photo SET link=? WHERE link="/seephoto?id="''', [link])
    db.commit()

def storeStdMessage(msg):
    """ Store a standard text message if new else update the link if it already exists in case when friend changes IP """
    db = sqlite3.connect("db/main.db")
    curs = db.cursor()
    creator = msg['creator']
    created = time.asctime(time.localtime(msg['created']))
    link = "http://" + "%s:%s" % (findIP(creator), findPort(creator)) + msg['link']
    body = msg['body']

    try:
        curs.execute('''SELECT link FROM message WHERE created=? AND creator=?''', [created, creator])
        oldLink = curs.fetchall()
        oldLink = oldLink[0][0]
        curs.execute('''UPDATE message SET link=? WHERE link=?''', [link, oldLink])
    except:
        curs.execute('''INSERT INTO message (creator, created, link, body) VALUES (?,?,?,?)''', [creator, created, link, body])
    db.commit()

def storeStdPhoto(msg):
    """ Store a standard photo message if new else update the link if it already exists in case when friend changes IP """
    db = sqlite3.connect("db/main.db")
    curs = db.cursor()
    creator = msg['creator']
    created = time.asctime(time.localtime(msg['created']))
    link = "http://" + "%s:%s" % (findIP(creator), findPort(creator)) + msg['link']
    body = msg['body']
    try:
        curs.execute('''SELECT link FROM photo WHERE created=? AND creator=?''', [created, creator])
        oldLink = curs.fetchall()
        oldLink = oldLink[0][0]
        curs.execute('''UPDATE photo SET link=? WHERE link=?''', [link, oldLink])
    except:
        curs.execute('''INSERT INTO photo (creator, created, link, body) VALUES (?,?,?,?)''', [creator, created, link, body])
    db.commit()

def storeStdEvent(msg):
    """ Store a standard event message if new else update the link if it already exists in case when friend changes IP """
    db = sqlite3.connect("db/main.db")
    curs = db.cursor()
    creator = msg['creator']
    created = time.asctime(time.localtime(msg['created']))
    link = "http://" + "%s:%s" % (findIP(creator), findPort(creator)) + msg['link']                   
    body = msg['body']
    year = msg['year']
    month = msg['month']
    day = msg['day']
    try:
        curs.execute('''SELECT link FROM event WHERE created=? AND creator=?''', [created, creator])
        oldLink = curs.fetchall()
        oldLink = oldLink[0][0]
        curs.execute('''UPDATE event SET link=? WHERE link=?''', [link, oldLink])
    except:
        curs.execute('''INSERT INTO event (creator, created, link, body, year, month, day) VALUES (?,?,?,?,?,?,?)''', [creator, created, link, body, year, month, day])
    db.commit()

def storeStdMessages(stdMessages):
    """ Store newly decoded messages received from a friend
        message type: 1 - text message, 2 - photo, 3 - event 
    """
    for msg in stdMessages:
        if msg['type'] == 1:
            storeStdMessage(msg)           
        if msg['type'] == 2:
            storeStdPhoto(msg)
        if msg['type'] == 3:
            storeStdEvent(msg)

def informServerImOn():
    """ Inform the central server (address server) that current user has just got online """
    try:
        fptr = urlopener.open("http://%s/iamhere?ip=%s&port=%s&id=%s" % (server_addr, ip, listen_port, userID, ))
        fptr.close()
    except: # central sever down
        pass

def removeFriend(friendID):
    """ Remove a friend while still keep his/her friend request by toggle his/her friend status 
        so just have to accept his/her request again in case want to make him/her a friend 
        anytime in the future 
    """
    db = sqlite3.connect('db/main.db')
    curs = db.cursor()
    curs.execute('''UPDATE friend SET friend=0 WHERE clientID=?''', [friendID]) # toggle his/her friend status
    db.commit()
    
    # update global friend list immediatly
    global friendList
    friendList.remove(friendID)

def encodeMessage(stdMessage):
    """ Take a standard message and turns it into a json encoded message """
    encodedMessage = {'message':json.dumps(stdMessage)}

    return encodedMessage

def pullUpdates():
    """ Pull all your online friends' updates and store them into the db """
    loadFriendList(userID)
    for friend in findOnlineFriends(friendList):
        try:
            fptr = urlopener.open("http://%s:%s/getActivity" % (findIP(friend), findPort(friend)))
            decodedMessages = json.loads(fptr.read()) # decode to standard messages
            storeStdMessages(decodedMessages)
            fptr.close()     
        except:
            pass

def sendUpdate(messageID, messageType):
    """ Post a new text or event or photo message update, specified by message id, to all your current online friend """
    if messageType == "text":
        encodeMsg = urllib.urlencode(encodeMessage(stdMessage(messageID)))
    if messageType == "event":
        encodeMsg = urllib.urlencode(encodeMessage(stdEvent(messageID)))
    if messageType == "photo":
        encodeMsg = urllib.urlencode(encodeMessage(stdPhoto(messageID)))
    loadFriendList(userID)
    for friend in findOnlineFriends(friendList):
        try:
            fptr = urlopener.open("http://%s:%s/sendActivity" % (findIP(friend), findPort(friend)), encodeMsg)
            fptr.close()
        except:
            pass

def getfPhotos():
    """ Get friends' photo links that are stored in host's db for gallery display """
    db = sqlite3.connect('db/main.db')
    curs = db.cursor()
    data = curs.execute('''SELECT link FROM photo WHERE creator IN (SELECT clientID FROM friend WHERE hostID=? and friend=1) ORDER BY id DESC''', [userID])
    photos = []
    for photo in data:
        photos.append(photo[0])

    return photos

def authenticateAll():
    """ Do authentication to all online friends to grant session cookies for identification """
    loadFriendList(userID)
    db = sqlite3.connect('db/main.db')
    curs = db.cursor()
    for friend in findOnlineFriends(friendList):
        data = curs.execute('''SELECT clientKey FROM friend WHERE hostID=? AND clientID=? AND friend=1''', [userID, friend])
        for secret in data:
            key = secret[0]
            try:
                fptr = urlopener.open("http://%s:%s/authenticate?serverID=%s&clientID=%s&key=%s" % (findIP(friend), findPort(friend), friend, userID, key)) 
                fptr.close()
            except:
                pass

def checkSignedIn():
    """ If not signed in send to default to block unauthorized access for user on host side """
    if not signedIn:
        raise cherrypy.HTTPRedirect("/default")

def DenyClientAccess():
    """ Deny client access to areas that are only accessible to user on host side """
    connectionIp = cherrypy.request.headers["Remote-Addr"]
    if connectionIp != ip:  
        raise cherrypy.HTTPRedirect("/default")

def getLastMessageID():
    """ Get the last row id in message table """
    db = sqlite3.connect('db/main.db')
    curs = db.cursor()
    # can't make table a subject of parameter in sqlite so this function can't be generalized
    curs.execute('''SELECT max(id) FROM message''') 

    return curs.fetchone()[0]

def getLastEventID():
    """ Get the last row id in event table """
    db = sqlite3.connect('db/main.db')
    curs = db.cursor()
    curs.execute('''SELECT max(id) FROM event''')

    return curs.fetchone()[0]

def getLastPhotoID():
    """ Get the last row id in photo table """
    db = sqlite3.connect('db/main.db')
    curs = db.cursor()
    curs.execute('''SELECT max(id) FROM photo''')

    return curs.fetchone()[0]

def passAuthentication():
    """ Check if this client has authenticated as a friend of user or not """
    uname = cherrypy.session.get('uname')
    if not uname:
        return False
    else:
        return True

def loginHandler(username, password):
    """ Handle login by checking if the password is correct or not
        Set current user id and inform central server if correct
        else reject 
    """
    global signedIn
    userPassword = getUserPassword(username)
    if password != None and password == userPassword:
        signedIn = True
        setuserID(username)
        informServerImOn()
        log.info("%s logged in." % (username, ))
    else:
        raise cherrypy.HTTPRedirect("/signin")

class MainApp(object):
    """ This app is small, so all requests will come through the MainApp object
    """

    # Turn ecoding on so the format will be right for jinja
    _cp_config = {'tools.encode.on': True, 
                  'tools.encode.encoding': 'utf8',
                 }

    @cherrypy.expose
    def css(self, fname):
        """ If they request a stylesheet, set the content type of
            the response, read the file, and dump it out in the response
            look in a "css" folder for the css files.
        """
        ext = os.path.splitext(fname)[1]
        if ext == ".css":
            cherrypy.response.headers['Content-Type'] = "text/css"
        f = open(css_folder+"/"+fname,"rb")
        data = f.read()
        f.close()

        return data

    @cherrypy.expose
    def default(self, *args, **kwargs):
        """ The default page, given when we don't recognise where the request is for.
        """
        connectionIp = cherrypy.request.headers["Remote-Addr"] 
        if connectionIp == ip: 
            # for users on host side, send to a sign in page 
            defaulturl = "/signin"
        else:
            # for clients outside of host machine, send it to a public page 
            defaulturl = "/public"
        
        raise cherrypy.HTTPRedirect(defaulturl)

    @cherrypy.expose
    def signin(self):
        """ Prompt the user with a login form. The form will be submitted to /home
            as a POST request, with arguments "username", "password" and "signin"
        """
        DenyClientAccess()
        page = env.get_template("signinpage.html")

        return page.render()

    @cherrypy.expose
    def signOut(self):
        """ The sign out place """
        DenyClientAccess()
        global signedIn
        signedIn = False

        raise cherrypy.HTTPRedirect("/default")

    @cherrypy.expose
    def home(self, username=None, password=None, action=None, message=None):
        """ Check user login for first time login
            Post new text message from user input and send it to all friends 
            Pull latest text message updates from online friends and display 
        """
        DenyClientAccess()
        # user signing in
        if not signedIn and action == 'Sign In':
            loginHandler(username, password)

        # a new message is posted by user
        if signedIn and action == "post" and message != None:
            storeMessage(message)
            authenticateAll()
            sendUpdate(getLastMessageID(), "text") # send it to friends online

        # display home page main content (text messages), user can refresh home page by clicking home on top menu
        if signedIn:
            loadFriendList(userID)
            authenticateAll()
            pullUpdates()
            page = env.get_template("homepage.html")
            return page.render(onlineFriendList=findOnlineFriends(friendList),
                                statusUpdates=getTexts(),
                                myAddr=myAddr)
        else:
            raise cherrypy.HTTPRedirect("/signin")

    @cherrypy.expose
    def register(self, username=None, password=None, name=None, sex=None, register=None):
        """ This is where all the users on the server side register their accounts """
        DenyClientAccess()
        createDb = sqlite3.connect('db/main.db')
        cursor = createDb.cursor()
        cursor.execute('''INSERT INTO user VALUES (?,?,?,?,"","",NULL,NULL,NULL)''', (username, password, name, sex))
        createDb.commit()
     
        page = env.get_template("register.html")

        return page.render()

    @cherrypy.expose
    def profile(self, profile=None, day=None, month=None, year=None, email=None, aboutme=None):
        """ This is where user can see user's own profile """
        DenyClientAccess()
        checkSignedIn()
        page = env.get_template("userprofilepage.html")
        db = sqlite3.connect("db/main.db")
        curs = db.cursor()
        if profile == "Submit":
            if day != None and day != "na":
                curs.execute('''UPDATE user SET day=? WHERE username=?''', [day, userID])
            if month != None and month != "na":
                curs.execute('''UPDATE user SET month=? WHERE username=?''', [month, userID])
            if year != None and year != "na":
                curs.execute('''UPDATE user SET year=? WHERE username=?''', [year, userID])
            if email != None and email != "":
                curs.execute('''UPDATE user SET email=? WHERE username=?''', [email, userID])
            if aboutme != None and aboutme != "":
                curs.execute('''UPDATE user SET aboutme=? WHERE username=?''', [aboutme, userID])
            db.commit() 

        return page.render(name=findUserInfo(userID)[2],
                            sex=findUserInfo(userID)[3],
                            email=findUserInfo(userID)[4],
                            aboutme=findUserInfo(userID)[5],
                            day=findUserInfo(userID)[6],
                            month=findUserInfo(userID)[7],
                            year=findUserInfo(userID)[8],
                            myAddr=myAddr)

    @cherrypy.expose
    def editProfile(self, editProfile=None):
        """ This is where user edits user's profile """
        DenyClientAccess()
        checkSignedIn()
        page = env.get_template("editprofilepage.html")
        
        return page.render(name=findUserInfo(userID)[2],
                            email=findUserInfo(userID)[4],
                            aboutme=findUserInfo(userID)[5],
                            day=findUserInfo(userID)[6],
                            month=findUserInfo(userID)[7],
                            year=findUserInfo(userID)[8],
                            myAddr=myAddr)

    @cherrypy.expose
    def event(self, day=None, month=None, year=None, description=None, event=None):
        """ Create events and view events, both user's and user's friends' """
        DenyClientAccess()
        checkSignedIn()
        authenticateAll()
        pullUpdates()
        page = env.get_template("eventpage.html")
        # a new event created by user
        if (event == "create"):
            storeEvent(day, month, year, description)
            authenticateAll()
            sendUpdate(getLastEventID(), "event") # send new update to online friends

        return page.render(events=getEvents(), onlineFriendList=findOnlineFriends(friendList), myAddr=myAddr)

    @cherrypy.expose
    def gallery(self, gallery=None):
        """ This is where user can view user's photos """
        DenyClientAccess()
        checkSignedIn()
        authenticateAll()
        pullUpdates()
        page = env.get_template("gallerypage.html")
        
        return page.render(photoes=getPhotos(), fphotoes=getfPhotos(), onlineFriendList=findOnlineFriends(friendList), myAddr=myAddr)

    @cherrypy.expose
    def uploadPhoto(self, newPhoto=None, uploadPhoto=None, body=None):
        """ This is where user can upload a photo """
        DenyClientAccess()
        checkSignedIn()
        page = env.get_template("uploadphotopage.html")
        # if a new photo is uploaded
        if uploadPhoto == "Upload":
            storePhoto(newPhoto, body)
            authenticateAll()
            sendUpdate(getLastPhotoID(), "photo") # send this new photo to online friends

        return page.render(onlineFriendList=findOnlineFriends(friendList), myAddr=myAddr)

    @cherrypy.expose
    def seephoto(self, id):
        """ Clients see host's photos through here """
        db = sqlite3.connect('db/main.db')
        curs = db.cursor()
        names = curs.execute('''SELECT name FROM photo WHERE id=?''', [id])
        for name in names:
            fname = name[0] 
        raise cherrypy.HTTPRedirect("/img?fname=%s" % fname)

    @cherrypy.expose
    def img(self, fname):
        """ If they request some media, for example images, set the content type of the response,
            read the file, and dump it out in the response.
        """
        ext = os.path.splitext(fname)[1]
        if ext == ".jpg":
            cherrypy.response.headers['Content-Type'] = "image/jpeg"
        elif ext == ".png":
            cherrypy.response.headers['Content-Type'] = "image/png"
        elif ext == ".gif":
            cherrypy.response.headers['Content-Type'] = "image/gif"
        else:
            cherrypy.response.headers['Content-Type'] = "image/unknown"

        f = open(staticfolder + "/img/" + fname, "rb")
        data = f.read()
        f.close()

        return data

    @cherrypy.expose
    def whoonline(self, onlinelist=None, whoonline=None):
        """ Show who else is online in network now.
            This only shows their IDs.
        """
        onlineList = findOnlineInfo()   
        onlineIDs = simpleOnlineList(onlineList, userID)
        page = env.get_template("onlinelistpage.html")

        return page.render(onlineList=onlineIDs, myAddr=myAddr)

    @cherrypy.expose
    def public(self, profile=None):
        """ This is the index page for all the clients """
        if profile == None:
            page = env.get_template("publicpage.html")
            return page.render(userIDs=findAllUsers(), myAddr=myAddr)
        else:
            username = profile
            page = env.get_template("profilepage.html")

            return page.render(name=findUserInfo(username)[2],
                                sex=findUserInfo(username)[3],
                                email=findUserInfo(username)[4],
                                aboutme=findUserInfo(username)[5],
                                day=findUserInfo(username)[6],
                                month=findUserInfo(username)[7],
                                year=findUserInfo(username)[8],
                                myAddr=myAddr)

    @cherrypy.expose
    def addFriend(self, name=None, requesterID=None, myID=None, key=None, addFriend=None):
        """ This is where client sends host the friend request
            Check if all details are entered by client
            If valid then store in host machine
        """
        if addFriend != 'Submit':
            page = "where is this?"
        # make sure client fills all details
        elif (name != None and requesterID != None and myID !=None and key != None):
            page = "OK! Request has been sent to the user"
            db = sqlite3.connect('db/main.db')
            curs = db.cursor()
            # in case if the same client has submitted another request then update client's name and key
            data = curs.execute('''SELECT clientID FROM friend WHERE hostID=? AND friend=0''', [userID])
            for person in data:
                if person[0] == requesterID:
                    curs.execute('''UPDATE friend SET hostKey=? WHERE clientID=? AND hostID=?''', [key, requesterID, userID])
                    curs.execute('''UPDATE friend SET name=? WHERE clientID=? AND hostID=?''',[name, requesterID, userID])
                    curs.execute('''UPDATE friend SET friend=0 WHERE clientID=? AND hostID=?''', [requesterID, userID])
                    db.commit()
                    return page
            # store the request for view 
            curs.execute('''INSERT INTO friend (name, clientID, hostID, hostKey, friend) VALUES (?,?,?,?,0)''', (name, requesterID, myID, key))
            db.commit()
        else:
            page = "Please fill in all details"

        return page

    @cherrypy.expose
    def friending(self, friending=None):
        """ This is where client fills in details for friend request
            Client will be ask to choose a key (hostKey) for entering host's machine in the future
            Client then has to manually store the hostKey on client's machine by going to client's edit friend page
        """
        if friending == 'Add Friend':
            page = env.get_template('friendingpage.html')
        else:
            page = "where is this?"

        return page.render(myAddr=myAddr)

    @cherrypy.expose
    def friendRequest(self, friendRequest=None):
        """ This is where user view all user's unapproved friend requests """
        DenyClientAccess()
        checkSignedIn()
        page = env.get_template("friendRequest.html")
        db = sqlite3.connect('db/main.db')
        curs = db.cursor()
        requesterdata = curs.execute('''SELECT clientID FROM friend WHERE hostID=? and friend=0''', [userID])
        requesters = []
        for data in requesterdata:
            requesters.append(data[0])
        return page.render(requesters=requesters, onlineFriendList=findOnlineFriends(friendList), myAddr=myAddr)

    @cherrypy.expose
    def friendRequestResponse(self, friendRequestResponse=None):
        """ This is where user reply to all user's friend requests """
        DenyClientAccess()
        checkSignedIn()
        if 'Accept' in friendRequestResponse:
            requesterId = friendRequestResponse.replace("Accept", "")
            db = sqlite3.connect('db/main.db')
            curs = db.cursor()
            curs.execute('''UPDATE friend SET friend=1 WHERE clientID=?''', [requesterId]) # turn friend status to valid
            db.commit()
            page = "OK! accepted" 
            page += requesterId
            page += "as a friend"
            loadFriendList(userID)
        elif 'Reject' in friendRequestResponse:
            requesterId = friendRequestResponse.replace("Reject", "")
            db = sqlite3.connect('db/main.db')
            curs = db.cursor()
            curs.execute('''DELETE FROM friend WHERE clientID=? AND hostID=?''', [requesterId, userID]) # delete request
            db.commit()
            page = "OK! rejected"       
            page += requesterId
            page += "as a friend"
        else:
            page = "where is this?"

        raise cherrypy.HTTPRedirect("/friendRequest")

    @cherrypy.expose
    def editFriend(self, person=None, key=None, editFriend=None):
        """ Add/un friend
            After host has request friendship on client's site, host has to come here and manully entered
            the clientKey that host has just entered for accessing client's site to store it for future use
        """
        DenyClientAccess()
        checkSignedIn()
        loadFriendList(userID)
        page = env.get_template('editfriendpage.html')
        if person != None:
            if editFriend == 'Submit': # delete a friend
                removeFriend(person)
            elif key != "" and editFriend == 'Add':
                db = sqlite3.connect('db/main.db')
                curs = db.cursor()
                # if doesn't have this client's record then insert new record and put in client key else just update client key
                curs.execute('''SELECT * FROM friend WHERE clientID=? AND hostID=?''', [person, userID])
                data = curs.fetchall()
                if data == []: 
                    curs.execute('''INSERT INTO friend (clientID, hostID, clientKey, friend) VALUES (?,?,?,0)''', (person, userID, key))
                else:
                    curs.execute('''UPDATE friend SET clientKey=? WHERE hostID=? AND clientID=?''', [key, userID, person])
                db.commit()

        return page.render(onlineFriendList=findOnlineFriends(friendList), friendList=friendList, myAddr=myAddr)

    @cherrypy.expose
    def sendActivity(self, message):
        """ This is the place where all user's friends post updates to the user """
        if not passAuthentication():
            return "Please authenticate!"

        try:
            msg = json.loads(message) # decode the message
        except:
            return "Error - couldn't JSON decode"

        storeStdMessages([msg]) # argument has to be a list since storeStdMessages() takes a list of message(s)
        
        return "ok! host have received"

    @cherrypy.expose
    def getActivity(self, minutes=48*60):
        """ This is where user's friends can pull from user the recent updates created in the last 48 hrs """
        if not passAuthentication():
            return "Please authenticate!"

        clientID = cherrypy.session.get('uname')
        updates = []
        db = sqlite3.connect('db/main.db')
        curs = db.cursor()
        curs.execute('''SELECT * FROM message WHERE creator=? ORDER BY id''', [userID])
        messageData = curs.fetchall()
        for message in messageData:
            if time.time() - time.mktime(time.strptime(message[2])) <= int(minutes) * 60: # if time valid
                updates.append(stdMessage(message[0]))
        
        photoData = curs.execute('''SELECT * FROM photo WHERE creator=? ORDER BY id''', [userID]) 
        for photo in photoData:
           if time.time() - time.mktime(time.strptime(photo[2])) <= int(minutes) * 60:
                updates.append(stdPhoto(photo[0]))

        eventData = curs.execute('''SELECT * FROM event WHERE creator=? ORDER BY id''', [userID])
        for event in eventData:
            if time.time() - time.mktime(time.strptime(event[2])) <= int(minutes) * 60:
                updates.append(stdEvent(event[0]))
                    
        reply = json.dumps(updates) # send as encoded json messages

        return reply

    @cherrypy.expose
    def authenticate(self, serverID=None, clientID=None, key=None, page=None):
        """ Return a page containing a session cookie that, when passed back to the server on future
            requests, will allow it to identify the same user is involved. 
        """
        cherrypy.session['uname'] = None
        reply = "<h1>Fail Authentication</h1>"
        db = sqlite3.connect('db/main.db')
        curs = db.cursor()
        data = curs.execute('''SELECT hostKey FROM friend WHERE clientID=? AND hostID=? AND friend=1''', [clientID, serverID])
        for secretKey in data:
            if key == secretKey[0]: # if given key is correct
                cherrypy.session['uname'] = clientID # assign a session to this client
                reply = "<h1>OK! Pass Authentication</h1>"
                reply += clientID
        return reply


# Tell Cherrypy to listen for connections on the configured address and port
cherrypy.config.update({'server.socket_host': listen_ip,
                        'server.socket_port': listen_port,
                        'tools.sessions.on': True,
                        'tools.sessions.storage_type':'file',
                        'tools.sessions.storage_path':'sessionData',
                       })  


# Create an instance of MainApp and tell Cherrypy to send all requests under / to it (ie all of them)
cherrypy.tree.mount(MainApp(), "/", config = {})

print "========================================"

# Start the web server
cherrypy.engine.start()

# And stop doing anything else. Let the web server take over
cherrypy.engine.block()
