from lib.common import Response
import time
import socket
import ssl


class RequestSender:
    def __init__(self, requestqueue, responsequeue, tlsConfig):
        self.requestqueue = requestqueue
        self.responsequeue = responsequeue
        self.use_tls = tlsConfig['use_tls']
        self.ssl_context = ssl.create_default_context() if self.use_tls else None
        if self.use_tls:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
            if tlsConfig['cert'] and tlsConfig['key']:
                self.ssl_context.load_cert_chain(certfile=tlsConfig['cert'], keyfile=tlsConfig['key'])

    def send(self):
        request = self.requestqueue.get()
        sock = socket.create_connection(request.destination)
        if self.use_tls:
            sock = self.ssl_context.wrap_socket(sock, server_hostname=request.destination[0])
        request.time = time.time()
        sock.send(request.request)
        resp = b""
        while True:
            data = sock.recv(1024)
            resp += data
            if not data or len(data) < 1024:
                break

        response = Response(request, resp, time.time())
        self.responsequeue.put(response)
        sock.close()
