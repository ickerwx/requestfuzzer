class Request:
    def __init__(self, requeststring, requestnum, destination):
        self.request = requeststring
        self.num = requestnum
        self.time = None
        self.destination = destination


class Response:
    def __init__(self, request, responsestring, timestamp):
        self.request = request
        self.response = responsestring
        self.time = timestamp
