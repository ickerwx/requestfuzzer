import queue
import re
import sqlite3
from abc import ABC, abstractmethod
from codecs import decode
from lib.common import ABORT_MSG, PLS_FINISH_MSG


class RecorderBase(ABC):
    @abstractmethod
    def processResponse(self):
        pass


class HTTPRequestRecorder(RecorderBase):
    def __init__(self, responsequeue, cmdqueue, dbpath):
        self.queue = responsequeue
        self.cmdqueue = cmdqueue
        self.dbpath = dbpath

    def check_table_exists(self):
        query = "SELECT count(name) FROM sqlite_master WHERE type='table' AND name='fuzzdata'"
        self.cursor.execute(query)
        return self.cursor.fetchone()[0] == 1

    def create_table(self):
        query = """CREATE TABLE fuzzdata (
            num INTEGER,
            host TEXT,
            port INTEGER,
            req_timestamp TEXT,
            request TEXT,
            req_length INTEGER,
            resp_timestamp TEXT,
            response TEXT,
            code TEXT,
            resp_length INTEGER)"""
        self.cursor.execute(query)

    def processResponse(self):
        # connection and cursor need to be instantiated here instead of the constructor b/c this method will be run in
        # a different thread than the constructor, and sqlite doesn't like that.
        self.connection = sqlite3.connect(self.dbpath)
        self.cursor = self.connection.cursor()
        query = "insert into fuzzdata values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        if not self.check_table_exists():
            self.create_table()
        while True:
            try:
                response = self.queue.get(timeout=1)
                try:
                    code = re.findall(r"HTTP/1.[01] (.*?)\r*\n", decode(response.text, "latin_1"))[0]
                except Exception:
                    code = "Unknown"
                try:
                    request_length = re.findall(r"Content-Length:\s*(\d+)", decode(response.request.text, "latin_1"))[0]
                except Exception:
                    # detect line endings: \n or \r\n?
                    lines = decode(response.request.text, "latin_1").split('\n')
                    end = '\r\n' if lines[0].endswith('\r') else '\n'

                    # split text at 2*end to get request headers and body
                    # then replace the content-length header with the correct value, if that header exists
                    _, body = decode(response.text, "latin_1").split(2*end, 1)
                    request_length = len(body)
                try:
                    response_length = re.findall(r"Content-Length:\s*(\d+)", decode(response.text, "latin_1"))[0]
                except Exception:
                    # detect line endings: \n or \r\n?
                    lines = decode(response.text, "latin_1").split('\n')
                    end = '\r\n' if lines[0].endswith('\r') else '\n'

                    # split text at 2*end to get request headers and body
                    # then replace the content-length header with the correct value, if that header exists
                    _, body = decode(response.text, "latin_1").split(2*end, 1)
                    response_length = len(body)
                request = response.request
                values = (request.num,)
                values += request.destination
                values += (request.time, request.text, request_length, response.time, response.text, code, response_length)
                self.cursor.execute(query, values)
                self.connection.commit()
                self.queue.task_done()
            except queue.Empty:
                pass
            try:
                recipient, message = self.cmdqueue.get_nowait()
                if recipient == 'recorder':
                    if message == ABORT_MSG:
                        self.cursor.close()
                        self.connection.close()
                        return
                    if message == PLS_FINISH_MSG and self.queue.empty():
                        self.cursor.close()
                        self.connection.close()
                        return
                    else:
                        self.cmdqueue.put((recipient, message))
                else:
                    self.cmdqueue.put((recipient, message))

            except queue.Empty:
                # if the command queue is empty, just continue
                pass
