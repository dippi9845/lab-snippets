from snippets.lab2 import *
import threading

# Uncomment this line to observe timeout errors more often.
# Beware: short timeouts can make demonstrations more difficult to follow.
# socket.setdefaulttimeout(5) # set default timeout for blocking operations to 5 seconds


class Connection:
    def __init__(self, socket: socket.socket, callback=None):
        self.__socket = socket
        self.local_address = self.__socket.getsockname()
        self.remote_address = self.__socket.getpeername()
        self.__notify_closed = False
        self.__callback = callback
        self.__receiver_thread = threading.Thread(target=self.__handle_incoming_messages, daemon=True)
        if self.__callback:
            self.__receiver_thread.start()

    @property
    def callback(self):
        return self.__callback or (lambda *_: None)
    
    @callback.setter
    def callback(self, value):
        if self.__callback:
            raise ValueError("Callback can only be set once")
        self.__callback = value
        if value:
            self.__receiver_thread.start()

    @property
    def closed(self):
        return self.__socket._closed
    
    def send(self, message):
        if not isinstance(message, bytes):
            message = message.encode()
            message = int.to_bytes(len(message), 2, 'big') + message
        self.__socket.sendall(message)

    def receive(self):
        length = int.from_bytes(self.__socket.recv(2), 'big')
        if length == 0:
            return None
        return self.__socket.recv(length).decode()
    
    def close(self):
        self.__socket.close()
        if not self.__notify_closed:
            self.on_event('close')
            self.__notify_closed = True

    def __handle_incoming_messages(self):
        try:
            while not self.closed:
                message = self.receive()
                if message is None:
                    break
                self.on_event('message', message)
        except Exception as e:
            if self.closed and isinstance(e, OSError):
                return # silently ignore error, because this is simply the socket being closed locally
            self.on_event('error', error=e)
        finally:
            self.close()

    def on_event(self, event: str, payload: str=None, connection: 'Connection'=None, error: Exception=None):
        if connection is None:
            connection = self
        self.callback(event, payload, connection, error)


class Client(Connection):
    def __init__(self, server_address, callback=None):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(address(port=0))
        sock.connect(address(*server_address))
        super().__init__(sock, callback)


class Server:
    def __init__(self, port, callback=None):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.bind(address(port=port))
        self.__listener_thread = threading.Thread(target=self.__handle_incoming_connections, daemon=True)
        self.__callback = callback
        if self.__callback:
            self.__listener_thread.start()

    @property
    def callback(self):
        return self.__callback or (lambda *_: None)
    
    @callback.setter
    def callback(self, value):
        if self.__callback:
            raise ValueError("Callback can only be set once")
        self.__callback = value
        if value:
            self.__listener_thread.start()
    
    def __handle_incoming_connections(self):
        self.__socket.listen()
        self.on_event('listen', address=self.__socket.getsockname())
        try:
            while not self.__socket._closed:
                socket, address = self.__socket.accept()
                connection = Connection(socket)
                self.on_event('connect', connection, address)
        except ConnectionAbortedError as e:
            pass # silently ignore error, because this is simply the socket being closed locally
        except Exception as e:
            self.on_event('error', error=e)
        finally:
            self.on_event('stop')

    def on_event(self, event: str, connection: Connection=None, address: tuple=None, error: Exception=None):
        self.__callback(event, connection, address, error)

    def close(self):
        self.__socket.close()


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

EXIT_MESSAGE = "<EXIT>\0"

class Peer:
    def __init__(self, port, peers=None, discover_peer=None):
        if peers is None:
            peers = set()
        self.peers = {address(*peer) for peer in peers}
        self._connnections = {}
        self.__peers_sockets = {}
        for peer in self.peers:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(peer)
            self._connnections[peer] = Connection(sock, self.__connetion_callback)
        self.__connection_tread = threading.Thread(target=self.__handle_incoming_connections, daemon=True)
        self.__connection_tread.start()
        self.__available_port = port + 1
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.bind(address(port=port))
        self.__socket.listen()
        print(f"Peer listening on {self.local_address}")
        

    @property
    def local_address(self):
        return self.__socket.getsockname()
    
    def send_all(self, message):
        if not isinstance(message, bytes):
            message = message.encode()
        for peer in self.peers:
            self._connnections[peer].send(message)

    def __connetion_callback(self, event, payload, connection : Connection, error):
        match event:
            case 'message':
                if payload.endswith(EXIT_MESSAGE):
                    print(f"Connection with peer {connection.remote_address} closed")
                    self.peers.remove(connection.remote_address)
                else:
                    print(message(payload, connection.remote_address))
            case 'error':
                print(error)
            case 'close':
                self.peers.remove(connection.remote_address)
                self.__peers_sockets[connection.remote_address].close()
                print(f"Connection with peer {connection.remote_address} closed")

    
    def __connect_to_a_peer(self, address, port):
        socket_tmp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_tmp.connect((address, port))
        port = int.from_bytes(socket_tmp.recv(4), "big")



    def __handle_incoming_connections(self):
        try:
            socket_tmp, address = self.__socket.accept()
            socket_tmp.sendall(int.to_bytes(self.__available_port, 4, "big"))
            socket_tmp.close()
            self.__peers_sockets[address]
            self.peers.add(address)
            self._connnections[address] = connection

        except Exception as e:
            print(e)

    def close(self):
        self.__socket.close()
