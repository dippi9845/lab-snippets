import socket
import threading
import psutil
import sys
from datetime import datetime



def address(ip='0.0.0.0:0', port=None):
    ip = ip.strip()
    if ':' in ip:
        ip, p = ip.split(':')
        p = int(p)
        port = port or p
    if port is None:
        port = 0
    assert port in range(0, 65536), "Port number must be in the range 0-65535"
    assert isinstance(ip, str), "IP address must be a string"
    return ip, port


def message(text: str, sender: str, timestamp: datetime=None):
    if timestamp is None:
        timestamp = datetime.now()
    return f"[{timestamp.isoformat()}] {sender}:\n\t{text}"


def local_ips():
    for interface in psutil.net_if_addrs().values():
        for addr in interface:
            if addr.family == socket.AF_INET:
                    yield addr.address

class Peer:
    def __init__(self, port, peers=None):
        if peers is None:
            peers = set()
        self.peers = {address(*peer) for peer in peers}
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socket.bind(address(port=port))

    @property
    def local_address(self):
        return self.__socket.getsockname()
    
    def send_all(self, message):
        if not isinstance(message, bytes):
            message = message.encode()
        for peer in self.peers:
            self.__socket.sendto(message, peer)

    def receive(self):
        message, address = self.__socket.recvfrom(1024)
        self.peers.add(address)
        return message.decode(), address

    def close(self):
        self.__socket.close()

class AsyncPeer(Peer):
    def __init__(self, port, peers=None, callback=None):
        super().__init__(port, peers)
        self.__receiver_thread = threading.Thread(target=self.__handle_incoming_messages, daemon=True)
        self.__callback = callback or (lambda *_: None)
        self.__receiver_thread.start()
    
    def __handle_incoming_messages(self):
        while True:
            message, address = self.receive()
            if message.endswith(EXIT_MESSAGE):
                self.peers.remove(address)
            self.on_message_received(message, address)

    def on_message_received(self, payload, sender):
        self.__callback(payload, sender)


peer = AsyncPeer(
    port = int(sys.argv[1]), 
    peers = [address(peer) for peer in sys.argv[2:]], 
    callback = lambda message, _: print(message)
)