from lib.common import Response
import socket
import ssl
import queue
from datetime import datetime
from abc import ABC, abstractmethod
from lib.common import ABORT_MSG, PLS_FINISH_MSG


class SenderBase(ABC):
    @abstractmethod
    def send(self):
        pass


class TCPRequestSender(SenderBase):
    def __init__(self, requestqueue, responsequeue, cmdqueue, tlsConfig):
        self.requestqueue = requestqueue
        self.responsequeue = responsequeue
        self.cmdqueue = cmdqueue
        self.use_tls = tlsConfig['use_tls']
        self.ssl_context = ssl.create_default_context() if self.use_tls else None
        if self.use_tls:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
            if tlsConfig['cert'] and tlsConfig['key']:
                self.ssl_context.load_cert_chain(certfile=tlsConfig['cert'], keyfile=tlsConfig['key'])

    def send(self):
        while True:
            try:
                request = self.requestqueue.get(timeout=1)
                sock = socket.create_connection(request.destination)
                if self.use_tls:
                    sock = self.ssl_context.wrap_socket(sock, server_hostname=request.destination[0])
                request.time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                sock.send(request.request)
                self.requestqueue.task_done()
                resp = b""
                while True:
                    data = sock.recv(1024)
                    resp += data
                    if not data or len(data) < 1024:
                        break
                sock.close()
                response = Response(request, resp, datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
                self.responsequeue.put(response)
            except queue.Empty:
                pass
            try:
                recipient, message = self.cmdqueue.get_nowait()
                if recipient == 'sender':
                    if message == ABORT_MSG:
                        return
                    if message == PLS_FINISH_MSG and self.requestqueue.empty():
                        return
                    else:
                        self.cmdqueue.put((recipient, message))
                else:
                    self.cmdqueue.put((recipient, message))
            except queue.Empty:
                # if the command queue is empty, just continue
                pass
