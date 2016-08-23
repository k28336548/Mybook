#!/usr/bin/python
""" The "address" server

    C.Coghill 2012

    We listen for nodes reporting their location to us, then return a list
    of recently seen nodes to anyone who asks.

    http://server:port/iamhere?ip=IPADDR,port=PORT,id=ID

    ID is a string of 4-64 characters


    http://server:port/whoonline

    returns a list of nodes, one per line.
    IP,PORT,ID,LASTSEEN
"""

# Requires:  CherryPy 3.1.2  (www.cherrypy.org)
#            Python  (We use 2.6)

# The address we listen for connections on
listen_ip = "127.0.0.1"
listen_port = 10001
online_datafile = "ONLINE_DATA"

# We only allow addresses in the given range
valid_ips = ["130.216.", "172.23.", "172.24.", "127.0."]


import cherrypy
import os
import json
import time
import logging as log

print "========================="
print "Address Server Starting Up..."

# Log any errors to the log file
log.basicConfig(filename="error.log", level=log.DEBUG)


def check_ip_valid(ip):
    """ Given a string containing a potential IP address, return True if it appears
        to be valid, or False if not.
    """
    log.debug("Testing IP '%s'"%(ip,))

    try:
        a,b,c,d = ip.split(".")
    except ValueError:   # not at least four numbers separated by stops
        log.debug("...rejected a.b.c.d check")
        return False

    if not len(ip.split(".")) == 4:  # exactly four numbers separated by stops
        log.debug("...rejected four dots check")
        return False

    for valid in valid_ips:   # in the range we use on the LAN?
        if ip.startswith(valid):
            return True

    log.debug("...rejected end")

    return False

def check_port_valid(port):
    """ Given a string containing a potential IP Port, return True if it appears
        to be valid, or False if not.
    """

    try:
        int_port = int(port)
    except ValueError:    # not a number
        log.debug("rejected port '%s' - not an int"%(port,))
        return False

    if int_port <= 0:
        log.debug("rejected port '%s' - negative or 0"%(port,))
        return False    # Negative or 0

    if int_port > 32000:
        log.debug("rejected port '%s' - out of range"%(port,))
        return False     # unlikely to be legitimate, well into the range used by NAT routers

    return True

def check_id_valid(id):
    """ Given a string containing a potential ID, return True if it appears
        to be valid, or False if not.
    """

    if len(id) < 4 or len(id) > 64:
        return False

    if "," in id:   # Can't contain a comma
        return False

    if "\n" in id:   # Can't contain a newline
        return False

    return True


class MainApp(object):
    """ Our app is small, so all requests will come through the MainApp object.
    """

    # To be honest, I can't remember what this is for, but things break without it
    # anyone? Bueller? Hello?
    _cp_config = {'tools.encode.on': True, 
                  'tools.encode.encoding': 'utf8',
                 }


    # If they try somewhere we don't know, catch it here and send them to the
    # right place.
    @cherrypy.expose
    def default(self, *args, **kwargs):
        """ The default page, given when we don't recognise where the request is for.
        """
        
        return "Address Server"


    @cherrypy.expose
    def iamhere(self, ip=None, port=None, id=None):
        """ Record the given details and return an "OK" status (if they were)
        """

        if not check_ip_valid(ip):
            raise cherrypy.HTTPError(400, "IP Address does not appear to be valid")

        if not check_port_valid(port):
            raise cherrypy.HTTPError(400, "Port does not appear to be valid")
 
        if not check_id_valid(id):
            raise cherrypy.HTTPError(400, "ID does not appear to be valid")

        online_dict = load_online_dict()
        online_dict["%s:%s"%(ip, port)] = { 'ip':   ip,
                                       'port': port,
                                       'id': id,
                                       'lastseen': time.time()
                                     }
    
        save_online_dict(online_dict) 

        return "Ok"


    @cherrypy.expose
    def whoonline(self):
        """ Return a list, one per line, of currently known online addresses,
            separated by commas. We filter out anything over an hour old

            ip,port,id,lastseen
        """

        online_by_date = {}
        online_dict = load_online_dict()

        # we create a new dictionary of all the nodes, keyed by their lastseen field.
        # this makes it easy to return them sorted by time.
        # If we have two nodes at exactly the same time, we might lose one, I'm assuming
        # this won't happen often, and if it does, it's not too critical.
        for k,v in online_dict.iteritems():
            online_by_date[v['lastseen']] = v

        one_hour_ago = time.time() - (60 * 60)
        times = online_by_date.keys()
        times.sort(reverse=True)
        page = ""
        for t in times:
            if t > one_hour_ago:
                node = online_by_date[t]
                page += "%(ip)s,%(port)s,%(id)s,%(lastseen)s\n" % (node)

        cherrypy.response.headers['Content-Type'] = "text/plain"
        return page


def load_online_dict():
    """ Read the dictionary of online nodes in from the file and
        return it.
    """

    try:
        fptr = open(online_datafile)
        data = fptr.read()
        fptr.close()
    except IOError:   # file doesn't exist, assume empty
        return {}

    try:
        decoded = json.loads(data)
    except ValueError:  # file not in right format?
        return {}

    return decoded

    
def save_online_dict(online_dict):
    """ Take the given dictionary of online nodes and write it out to
        the data file.
    """

    fptr = open(online_datafile,"w")
    fptr.write(json.dumps(online_dict))
    fptr.close()
    return True


# Tell Cherrypy to listen for connections on the configured address and port.
cherrypy.config.update({'server.socket_host': listen_ip,
                        'server.socket_port': listen_port
                       })     


# Create an instance of MainApp and tell Cherrypy to send all requests under / to it. (ie all of them)
cherrypy.tree.mount(MainApp(), "/", config = {})

print "========================================"

# Start the web server
cherrypy.engine.start()

# And stop doing anything else. Let the web server take over.
cherrypy.engine.block()
