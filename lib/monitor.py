class Monitor:
    def __init__(self, reqq, resq):
        self.reqq = reqq
        self.resq = resq

    def stats(self):
        print(f"Request queue: {self.reqq.qsize()} Response queue: {self.resq.qsize()}         ", end="\r")

    def queues_are_empty(self):
        return self.reqq.qsize() == 0 and self.resq.qsize() == 0
