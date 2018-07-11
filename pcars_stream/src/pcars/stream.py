from pcars.packet import Packet
from io import BytesIO
from threading import Thread
import socket
import struct


_MCAST_ANY = "127.0.0.1"
print("_MCAST_ANY", _MCAST_ANY)

class PCarsStreamReceiver(Thread):

    def __init__(self, port=5606):
        super(PCarsStreamReceiver, self).__init__()
        self.port = port
        self.setDaemon(True)
        self.listeners = []

    def addListener(self, listener):
        self.listeners.append(listener)

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Bind to the server address
        # sock.bind(("", self.port))
        # group = socket.inet_aton(_MCAST_ANY)
        # mreq = struct.pack("4sL", group, socket.INADDR_ANY)
        # sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("::1", self.port))

        while True:
            try:
                data = sock.recv(1400)
                # print(data)
                packet = Packet.readFrom(BytesIO(data))
                for listener in self.listeners:
                    listener.handlePacket(packet)
            except Exception as ex:
                print("Error in stream.py : ",ex)