#!/usr/bin/env python
#-*- coding:utf-8 -*-



#      0                   1                   2                   3
#      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
#     +-+-+-+-+-------+-+-------------+-------------------------------+
#     |F|R|R|R| opcode|M| Payload len |    Extended payload length    |
#     |I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
#     |N|V|V|V|       |S|             |   (if payload len==126/127)   |
#     | |1|2|3|       |K|             |                               |
#     +-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
#     |     Extended payload length continued, if payload len == 127  |
#     + - - - - - - - - - - - - - - - +-------------------------------+
#     |                               |Masking-key, if MASK set to 1  |
#     +-------------------------------+-------------------------------+
#     | Masking-key (continued)       |          Payload Data         |
#     +-------------------------------- - - - - - - - - - - - - - - - +
#     :                     Payload Data continued ...                :
#     + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
#     |                     Payload Data continued ...                |
#     +---------------------------------------------------------------+
#

# unfragmented message  FIN = 1 && opcode > 0
# 
# fragmented message   FIN = 0 && opcode > 0
#                     [FIN = 0 && opcode == 0] *
#                      FIN = 1 && opcode == 0
#
# opcode (see '5.6.  Data Frames' )
#        0x1 --> text utf-8
#        0x2 --> binary      
#        0x8 --> close
#        0x9 --> ping
#        0xA --> pong



import asyncore
import socket
import struct
import array

import hashlib
from base64 import b64encode
from random import randint

from time import sleep

class FrameEncodeur( object ) :

    class Masked( object ):
        def mask_frame(self, frame, data ) :
            keys = ( randint(0, 255), randint(0, 255), randint(0, 255), randint(0, 255) )
            j = array.array( 'B', data )
            for i in xrange(len(j)):
                j[i] ^= keys[i % 4]

            frame.data = j.tostring()
            frame.bytes[1] += 128
            frame.masking_key = "".join( chr( k ) for k in keys )

    class Unmasked( object ) :
        def mask_frame(self, frame, data ) :
            print "Unmasked.mask_frame", data
            frame.data = data

    class UnFragmented( object ):
        def fragmente( self, frame ):
            print "UnFragmented.fragmente"
            frame.bytes[0] += 128
            length = len( frame.data )
            if length < 126 :      
                frame.bytes[1] += length
            elif length < 65536 :
                frame.bytes[1] += 126
                frame.bytes.extend( struct.pack('!H', length) )
            else : # Length must be lower than 9 223 372 036 854 775 808  ( :-/ why not... )
                frame.bytes[1] += 127
                frame.bytes.extend( struct.pack('!Q', length) )

    class Fragmented( object ):
        def fragmente(self, frame ):
            pass

    def __init__( self ) :
        self.masked = self.Unmasked()
        self.fragmented = self.UnFragmented()
        self.bytes = [0,0]
        self.masking_key = ''
        self.data = ''

    def encode( self, data ) :
        """
        Return a tuple of encoded frame.
        """
        # RAZ
        print "FrameEncodeur.encode", data
        self.masking_key = ''
        self.data = ''

        self.masked.mask_frame( self, data )
        self.fragmented.fragmente( self )
        print "BYTES", self.bytes
        return  "".join( [ chr(e) for e in self.bytes ] ) + self.masking_key + self.data




class PingFrame( FrameEncodeur ) :
    def __init__( self ) :
        FrameEncodeur.__init__( self )
        self.bytes[ 0x9, 0 ]

    def encode( self, data ) :
        self.bytes = [ 0x9, 0 ]
        print "TextFrame.encode", data
        return super( TextFrame, self ).encode( data )


class PongFrame( FrameEncodeur ) :
    def __init__( self ) :
        FrameEncodeur.__init__( self )
        self.bytes[ 0xA, 0 ]

    def encode( self, data ) :
        self.bytes = [ 0xA, 0 ]
        print "TextFrame.encode", data
        return super( TextFrame, self ).encode( data )


class BinaryFrame( FrameEncodeur ) :   
    def __init__( self ) :
        FrameEncodeur.__init__( self )
        self.bytes = [ 0x2, 0 ]

    def encode( self, data ) :
        self.bytes = [ 0x2, 0 ]
        print "TextFrame.encode", data
        return super( TextFrame, self ).encode( data )


class TextFrame( FrameEncodeur ) :
    def __init__( self ) :
        FrameEncodeur.__init__( self )
        self.bytes = [ 0x1, 0 ]

    def encode( self, data ) :
        self.bytes = [ 0x1, 0 ]
        print "TextFrame.encode", data
        return super( TextFrame, self ).encode( data )


class CloseFrame( FrameEncodeur ) :
    def __init__( self ) :
        FrameEncodeur.__init__( self )
        self.bytes[ 0x8, 0 ]

    def encode( self, data ) :
        self.bytes = [ 0x8, 0 ]
        print "TextFrame.encode", data
        return super( TextFrame, self ).encode( data )


class WebSocketBuilder(object) :
    """
    Handshake part of protocol.
    """
    
    def __init__(self, socket, addr ) :
        self.answer_template = (
            'HTTP/1.1 101 Switching Protocols\r\n'
            'Upgrade: websocket\r\n'
            'Connection: Upgrade\r\n'
            'Sec-WebSocket-Accept: {accept}\r\n'
            'Sec-WebSocket-Protocol: chat\r\n'
            'Sec-WebSocket-Origin: {origine}\t\n'
            'Sec-WebSocket-Location: {location}\t\n'
            'Sec-WebSocket-Version: {version}\r\n\r\n' )

        self.addr = addr
        self.socket = socket
        self.headers = {}

    def send_handshake( self ) :
        self.__read_header()
        self.socket.send( self.answer_template.format( 
                                 accept=self.__gen_accept(),
                                 version=13, 
                                 origine=self.headers['Origin'], 
                                 location=self.headers['Host'] ) )
        print "SEND Handshake"
        return self.socket, self.addr

    def __read_header(self) :
        data = self.socket.recv(1024) 
        for line in data.splitlines()[1 : -1] : # First line like 'GET /chat HTTP/1.1'
            k, v = line.split( ': ', 1)
            self.headers[k] = v

    def __gen_accept(self) :
        return b64encode( hashlib.sha1( self.headers['Sec-WebSocket-Key'] + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11" ).digest() )




class WebSocketHandler(asyncore.dispatcher_with_send):

    def __init__( self, sock=None, map=None, clients=None ) :
        asyncore.dispatcher_with_send.__init__(self, sock, map)
        self._clients = clients
        self._masking_key = None
        self._payload_len = 0
        self.opcode = None
        self.fin = None
        self.frame_encodeur = TextFrame()


    _send = asyncore.dispatcher_with_send.send

    def __read_frame_byte_1( self ) :
        """
        EXAMPLE: For a text message sent as three fragments, the first
        fragment would have an opcode of 0x1 and a FIN bit clear, the
        second fragment would have an opcode of 0x0 and a FIN bit clear,
        and the third fragment would have an opcode of 0x0 and a FIN bit
        that is set.

        Pour les non fragment: FIN bit clear and opcode other than 0 
        """

        fin_rsv_opcode = ord( self._sock.recv(1) )
        if fin_rsv_opcode & 128 :
            self.fin = True
            print "FIN"
        else :
            self.fin = False
            print "FIRST FRAGMENT"

        if fin_rsv_opcode & 64 : #rsv 1
            print "rsv 1"
        if fin_rsv_opcode & 32 : #rsv 2
            print "rsv 2"
        if fin_rsv_opcode & 16 : #rsv 3
            print "rsv 3"

        self.opcode = fin_rsv_opcode & 15
        if self.opcode == 0x1 :    # see '5.6.  Data Frames'
            print 'text (utf-8)'
        elif self.opcode == 0x2 :  # see '5.6.  Data Frames'
            print 'binary'
        elif self.opcode == 0x8 :
            print "opcode == close" # FIXME RCF '5.5.1.  Close' Server must send close frame and close socket.
        elif self.opcode == 0x9 :
            print "opcode == ping"
        elif self.opcode == 0xA :
            print "opcode == pong"
        else :
            print "opcode ==", self.opcode


    def __read_mask_payload_len( self ) :
        mask_payload_len = ord( self._sock.recv(1) )
        is_masked = mask_payload_len & 128
        self._payload_len = mask_payload_len & 127
        if self._payload_len == 126 :
            bytes = self._sock.recv( 2 )
            self._payload_len = struct.unpack("!H", bytes)[0]

        elif self._payload_len == 127 :
            bytes = self._sock.recv( 8 )
            self._payload_len = struct.unpack("!Q", bytes)[0]

        if is_masked :  # Only messages from the client to the server are encoded (always), so your should only expect this to be 1.
            self._masking_key = self._sock.recv( 4 )
        else :
            self._masking_key = None


    @staticmethod
    def __unmask( masking_key, bytes) :
        keys = array.array( 'B', masking_key ) 
        new_bytes = array.array('B', bytes)
        i = 0
        try :
            while True :
                for k in keys :
                    new_bytes[i] ^= k
                    i+=1
        except IndexError :
            return new_bytes.tostring()


    def send( self, msg ) :
        print "WebSocketHandler.send '{}' (len {})".format( msg, len( msg ) )
        data = self.frame_encodeur.encode( msg )
        self._send(data)

    def send_all( self, msg ) :
        print "WebSocketHandler.send_all '{}' (len {})".format( msg, len( msg ) )
        data = self.frame_encodeur.encode( msg )
        for client in self._clients :
           client._send(data)

    def send_others( self, msg ) :
        print "WebSocketHandler.send_others '{}' (len {})".format( msg, len( msg ) )
        data = self.frame_encodeur.encode( msg )
        for client in self._clients :
            if client is not self : 
               client._send(data)
        
    def on_message(self, message):
        """
        You must redefine this function.
        """

    def handle_read(self):
        self.__read_frame_byte_1()
        self.__read_mask_payload_len()
        data = self.recv( self._payload_len )
        if self._masking_key is not None :
            data = self.__unmask( self._masking_key, data )
        self.on_message( data )

    def handle_close(self):
        self.close()
        self._clients.remove( self )


class WebSocketServer(asyncore.dispatcher):

    def __init__(self, host, port, web_socket_class ):
        asyncore.dispatcher.__init__(self)
        self.web_socket_class = web_socket_class 
        self.clients = list()
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind((host, port))
        self.listen(5)
        self._connect_listener = []

    def handle_accept(self):
        pair = self.accept()
        if pair is not None :
            sock, addr = pair
            sock, addr = WebSocketBuilder( sock, addr ).send_handshake()
            for listener in self._connect_listener :
                listener( sock, addr )
            self.clients.append( self.web_socket_class( sock, clients=self.clients ) )


    def add_connect_listener( self, listener ) :
        """
        listener must be callable wich take two arguments
        WebSocketHandler object and ip_addr
        """
        if not callable( listener ) :
            raise ValueError( 'listener must be callable' )
        self._connect_listener.append( listener )


    def start(self) :
        """
        Run server
        """
        asyncore.loop()

if __name__ == '__main__' :
    # How to use cormier ?
    #
    # Exemple: 
    # Subclass WebSocketHandler and redefine on_message method.
    # on_message method is called when client send message.
    class WebSocket( WebSocketHandler ) :
        def on_message(self, message ) :
            print "WebSocket.on_message", message
            self.send( 'R: ' + message ) # Send to the client.
            self.send_others( message )  # Send to the others clients.

    
    def connect_listener( web_socket, addr ) :
        print 'Incoming connection from %s' % repr(addr)


    server = WebSocketServer('localhost', 9003, WebSocket )
    server.add_connect_listener( connect_listener ) # When new client connection, the connect_listener function is called.
    server.start() # Run server.

