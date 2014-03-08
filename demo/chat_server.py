#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""
Mini chat server exemple
"""

import sys, os
sys.path.append( os.path.join( os.path.realpath( os.path.dirname( __file__ ) ), os.pardir ) )


from cormier import WebSocketHandler, WebSocketServer


# Subclass WebSocketHandler and redefine on_message method.
# on_message method is called when client send message.
class WebSocket( WebSocketHandler ) :
    def on_message(self, message ) :
        print "WebSocket.on_message", message
        self.send( 'R: ' + message ) # Send to the client.
        self.send_others( message )  # Send to the others clients.


# Create a connect_listener to log connection (optional)
def connect_listener( web_socket, addr ) :
    print 'Incoming connection from %s' % repr(addr)


server = WebSocketServer('localhost', 9003, WebSocket )
server.add_connect_listener( connect_listener ) # When new client connection, the connect_listener function is called.
server.start() # Launch server.
