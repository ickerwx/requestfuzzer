class Request:
    def __init__(self, requeststring, requestnum, destination):
        self.text = requeststring
        self.num = requestnum
        self.time = None
        self.destination = destination


class Response:
    def __init__(self, request, responsestring, timestamp):
        self.request = request
        self.text = responsestring
        self.time = timestamp


ABORT_MSG = 'abort abort abort!'
PLS_FINISH_MSG = 'please finish, then go'
