import time


class Monitor:
    def __init__(self, reqq, resq):
        self.reqq = reqq
        self.resq = resq

    def stats(self):
        while True:
            now = time.time()
            while time.time() - now < 5:
                time.sleep(1)
            print(f"Request queue: {self.reqq.qsize()}\nResponse queue: {self.resq.qsize()}")
