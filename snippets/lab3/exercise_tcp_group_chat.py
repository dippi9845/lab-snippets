import socket
import threading
import psutil
import sys
from datetime import datetime
from snippets.lab3 import *


peer = Peer(
    port = int(sys.argv[1]), 
    peers = [address(peer) for peer in sys.argv[2:]]
)